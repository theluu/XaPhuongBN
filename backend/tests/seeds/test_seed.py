from decimal import Decimal

from sqlalchemy import func, select

from app.catalog.models import Indicator, Program, Scenario
from app.core.db import admin_sessionmaker
from app.indicators.models import IndicatorValue
from app.platform.models import Tenant
from seeds.run import purge_sample, seed_platform, seed_tenant


async def _vy() -> int:
    await seed_platform()
    return await seed_tenant("viet_yen", with_sample=True)


async def _inds(t: int) -> dict[str, Indicator]:
    async with admin_sessionmaker()() as s:
        return {i.ma_chi_tieu: i for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == t))).scalars()}


async def test_seed_nq01_exact_targets():
    t = await _vy()
    inds = await _inds(t)
    nq = {k: v for k, v in inds.items() if "NQ01" in (v.bo or [])}
    assert len(nq) == 23
    assert inds["NQ01-12"].muc_tieu_2030 == Decimal("99.8")
    assert inds["NQ01-11"].muc_tieu_2030 == Decimal("88.9")
    assert inds["NQ01-09"].muc_tieu_2030 == Decimal("95")
    assert inds["NQ01-10"].chieu == "giam_tot" and inds["NQ01-10"].muc_tieu == 0 and inds["NQ01-10"].han_muc_tieu_nam == 2027
    assert inds["NQ01-05a"].muc_tieu_khoang == [15, 18] and inds["NQ01-05b"].muc_tieu_khoang == [12, 15]
    assert inds["NQ01-01a"].nguong_toan_tu == ">" and inds["NQ01-01a"].muc_tieu == 90
    assert inds["NQ01-13a"].muc_tieu == 98 and inds["NQ01-13b"].muc_tieu == 95 and inds["NQ01-13c"].muc_tieu == 97
    assert inds["NQ01-16"].muc_tieu_2030 == 15
    for i in nq.values():
        assert i.dinh_nghia and i.cong_thuc and i.pham_vi_dia_ban and i.don_vi_chu_quan


async def test_nq01_13_not_derived_from_tthc():
    t = await _vy()
    i = (await _inds(t))["NQ01-13a"]
    assert i.phan_he == "tthc_pakn" and i.nhom == "ktxh"
    assert "TTHC" not in i.cong_thuc and "đơn thư" in i.cong_thuc.lower()
    assert "Không gộp" in i.ghi_chu


async def test_programs_and_scenarios_placeholders():
    t = await _vy()
    async with admin_sessionmaker()() as s:
        progs = list((await s.execute(select(Program).where(Program.tenant_id == t))).scalars())
        scs = list((await s.execute(select(Scenario).where(Scenario.tenant_id == t))).scalars())
    assert len(progs) == 8
    assert len(scs) == 17 and sum(sc.la_bo_sung for sc in scs) == 2


async def test_seed_idempotent():
    t1 = await _vy()
    n1 = len(await _inds(t1))
    t2 = await _vy()
    assert t1 == t2 and len(await _inds(t2)) == n1


async def test_sample_flagged():
    t = await _vy()
    async with admin_sessionmaker()() as s:
        rows = list((await s.execute(select(IndicatorValue).where(IndicatorValue.tenant_id == t))).scalars())
    assert rows and all(r.is_sample for r in rows)


async def test_purge_sample_data():
    t = await _vy()
    n = await purge_sample("viet_yen")
    assert n > 0
    async with admin_sessionmaker()() as s:
        left = (await s.execute(select(func.count()).select_from(IndicatorValue).where(IndicatorValue.tenant_id == t))).scalar()
        assert left == 0
        assert (await s.get(Tenant, t)) is not None
    assert len(await _inds(t)) >= 23
    await seed_tenant("viet_yen", with_sample=True)  # khôi phục cho test khác
