"""Seed nền tảng & đơn vị.

    python -m seeds.run platform
    python -m seeds.run tenant viet_yen [--with-sample]
    python -m seeds.run purge-sample viet_yen
    python -m seeds.run demo            # platform + viet_yen + dữ liệu minh họa
"""
import asyncio
import os
import sys
from pathlib import Path

import yaml
from sqlalchemy import delete, select, text

from app.auth.models import Grant, User
from app.auth.roles import default_grants
from app.auth.security import hash_password
from app.catalog.models import Indicator, TemplatePack
from app.catalog.packs import apply_pack
from app.core.db import Base, admin_sessionmaker, import_models
from app.platform.models import ResidentialGroup, SharedCatalog, Tenant
from app.sources.service import ensure_default_sources

HERE = Path(__file__).parent


def _yaml(rel: str) -> dict:
    return yaml.safe_load((HERE / rel).read_text(encoding="utf-8"))


async def seed_platform() -> None:
    import_models()
    async with admin_sessionmaker()() as s:
        for loai, items in _yaml("catalogs/shared.yaml").items():
            for it in items:
                row = (await s.execute(select(SharedCatalog).where(SharedCatalog.loai == loai, SharedCatalog.ma == it["ma"]))).scalar()
                if row is None:
                    s.add(SharedCatalog(loai=loai, ma=it["ma"], ten=it["ten"], thuoc_tinh=it.get("thuoc_tinh", {})))
                else:
                    row.ten, row.thuoc_tinh = it["ten"], it.get("thuoc_tinh", {})
        for f in sorted((HERE / "packs").glob("*.yaml")):
            pack = yaml.safe_load(f.read_text(encoding="utf-8"))
            row = (await s.execute(select(TemplatePack).where(TemplatePack.ma == pack["ma"]))).scalar()
            if row is None:
                s.add(TemplatePack(ma=pack["ma"], ten=pack["ten"], phien_ban=pack["phien_ban"], noi_dung=pack))
            else:
                row.ten, row.phien_ban, row.noi_dung = pack["ten"], pack["phien_ban"], pack
        await ensure_default_sources(s)
        await s.commit()


async def _tenant(s, spec: dict, parent_id: int | None = None) -> Tenant:  # noqa: ANN001
    t = (await s.execute(select(Tenant).where(Tenant.ma_dvhc == spec["ma_dvhc"]))).scalar()
    if t is None:
        t = Tenant(ma_dvhc=spec["ma_dvhc"], ten=spec["ten"], cap=spec["cap"], parent_id=parent_id,
                   config=spec.get("config", {}), modules=spec.get("modules", {}))
        s.add(t)
        await s.flush()
    return t


async def seed_tenant(code: str, with_sample: bool = False) -> int:
    spec = _yaml(f"tenants/{code}/tenant.yaml")
    password = os.environ.get("SEED_PASSWORD") or "Demo@2026"
    async with admin_sessionmaker()() as s:
        platform = await _tenant(s, spec["platform"])
        parent = await _tenant(s, spec["parent"], platform.id)
        t = await _tenant(s, spec["tenant"], parent.id)
        pack = (await s.execute(select(TemplatePack).where(TemplatePack.ma == spec["pack"]))).scalar_one()
        await apply_pack(s, t.id, pack.noi_dung)
        for i in range(1, spec["so_tdp"] + 1):
            ma = f"TDP{i:02d}"
            if (await s.execute(select(ResidentialGroup.id).where(ResidentialGroup.tenant_id == t.id, ResidentialGroup.ma_tdp == ma))).scalar() is None:
                s.add(ResidentialGroup(tenant_id=t.id, ma_tdp=ma, ten=f"Tổ dân phố số {i}"))
        ids: dict[str, int] = {}
        for u in spec["users"]:
            row = (await s.execute(select(User).where(User.username == u["username"]))).scalar()
            tid = platform.id if u.get("platform") else t.id
            if row is None:
                row = User(tenant_id=tid, username=u["username"], ho_ten=u["ho_ten"], chuc_danh=u["chuc_danh"],
                           don_vi=spec["tenant"]["ten"] if not u.get("platform") else "Nền tảng", trang_thai="hoat_dong",
                           password_hash=hash_password(password))
                s.add(row)
                await s.flush()
                for g_nhom, g_quyen in default_grants(u["role"], u.get("nhom")):
                    s.add(Grant(user_id=row.id, tenant_id=tid, role=u["role"], nhom_du_lieu=g_nhom, quyen=g_quyen))
            ids[u["username"]] = row.id
        await s.commit()
        if with_sample:
            await _seed_sample(s, t.id, ids)
        return t.id


async def _seed_sample(s, tenant_id: int, users: dict[str, int]) -> None:  # noqa: ANN001
    from seeds.sample import indicators as sample_ind

    await purge_sample_by_id(s, tenant_id)
    inds = {i.ma_chi_tieu: i for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tenant_id))).scalars()}
    from app.catalog.models import IndicatorPlan

    await s.execute(delete(IndicatorPlan).where(IndicatorPlan.tenant_id == tenant_id))
    xn = {n: users.get("xacnhan") for n in ["ktxh", "dan_cu", "cong_trinh", "tthc_pakn", "gd_yt_mt"]} | {"ngan_sach": users.get("ketoan")}
    s.add_all(sample_ind.build(inds, tenant_id, users.get("canbo1"), xn))
    for mod in _sample_modules():
        await mod.seed(s, tenant_id, users)
    await s.commit()


def _sample_modules() -> list:
    """Các phân hệ đăng ký dữ liệu minh họa của mình trong seeds/sample/<phân hệ>.py (hàm seed)."""
    import importlib
    import pkgutil

    import seeds.sample as pkg

    mods = []
    for m in pkgutil.iter_modules(pkg.__path__):
        if m.name != "indicators":
            mod = importlib.import_module(f"seeds.sample.{m.name}")
            if hasattr(mod, "seed"):
                mods.append(mod)
    return mods


async def purge_sample_by_id(s, tenant_id: int) -> int:  # noqa: ANN001
    import_models()
    n = 0
    for table in reversed(Base.metadata.sorted_tables):
        if "is_sample" in table.c and "tenant_id" in table.c:
            r = await s.execute(text(f'DELETE FROM "{table.name}" WHERE tenant_id = :t AND is_sample'), {"t": tenant_id})
            n += r.rowcount or 0
    await s.flush()
    return n


async def purge_sample(code: str) -> int:
    spec = _yaml(f"tenants/{code}/tenant.yaml")
    async with admin_sessionmaker()() as s:
        t = (await s.execute(select(Tenant).where(Tenant.ma_dvhc == spec["tenant"]["ma_dvhc"]))).scalar_one()
        n = await purge_sample_by_id(s, t.id)
        await s.commit()
        return n


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    cmd = args[0]
    if cmd == "platform":
        asyncio.run(seed_platform())
    elif cmd == "tenant":
        asyncio.run(seed_tenant(args[1], with_sample="--with-sample" in args))
    elif cmd == "purge-sample":
        print(f"Đã xóa {asyncio.run(purge_sample(args[1]))} bản ghi minh họa")
    elif cmd == "demo":
        async def _demo() -> None:
            from app.core.bootstrap import bootstrap

            await bootstrap()
            await seed_platform()
            await seed_tenant("viet_yen", with_sample=True)

        asyncio.run(_demo())
    else:
        print(__doc__)
        sys.exit(1)
    print("Xong")


if __name__ == "__main__":
    main()
