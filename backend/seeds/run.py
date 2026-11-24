"""Seed nền tảng & đơn vị.

    python -m seeds.run platform
    python -m seeds.run tenant viet_yen [--with-sample]
    python -m seeds.run purge-sample viet_yen
    python -m seeds.run demo            # platform + viet_yen + nenh + dữ liệu minh họa
"""
import asyncio
import os
from datetime import date
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
    elif spec.get("config"):  # bổ sung khóa cấu hình mới của bộ demo, không ghi đè phần đơn vị đã chỉnh
        missing = {k: v for k, v in spec["config"].items() if k not in (t.config or {})}
        if missing:
            t.config = {**(t.config or {}), **missing}
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
                s.add(ResidentialGroup(tenant_id=t.id, ma_tdp=ma, ten=f"Tổ dân phố số {i}", loai="tdp"))
        ids: dict[str, int] = {}
        for u in spec["users"]:
            row = (await s.execute(select(User).where(User.username == u["username"]))).scalar()
            tid = platform.id if u.get("platform") else t.id
            if row is None:
                row = User(tenant_id=tid, username=u["username"], ho_ten=u["ho_ten"], chuc_danh=u["chuc_danh"],
                           don_vi="Nền tảng" if u.get("platform") else (u.get("don_vi") or (u["chuc_danh"].split(" – ")[0] if u["role"] == "chuyen_nganh" else spec["tenant"]["ten"])),
                           trang_thai="hoat_dong",
                           password_hash=hash_password(password))
                s.add(row)
                await s.flush()
                for g_nhom, g_quyen in default_grants(u["role"], u.get("nhom")):
                    s.add(Grant(user_id=row.id, tenant_id=tid, role=u["role"], nhom_du_lieu=g_nhom, quyen=g_quyen))
            ids[u.get("key", u["username"])] = row.id
        from app.dau_moi.service import ensure as ensure_dau_moi

        await ensure_dau_moi(s, t.id, t.ten)
        await s.commit()
        if with_sample:
            from seeds.sample import ho_so

            ho_so.chon(code)
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
    await _sample_alerts(tenant_id, users)
    await _sample_cong_bo(tenant_id, users)


async def _sample_cong_bo(tenant_id: int, users: dict[str, int]) -> None:
    """Công bố sẵn vài kỳ gần nhất ra trang công khai (bản minh họa) để demo trang chủ phường."""
    from datetime import date

    from app.cong_khai.models import CongBo
    from app.cong_khai.service import build_snapshot

    d = date.today()
    kys = []
    for k in range(4, 0, -1):  # 4 tháng đã chốt gần nhất (không gồm tháng đang chạy)
        m = d.month - k
        y = d.year + (m - 1) // 12
        kys.append(f"{y}-{(m - 1) % 12 + 1:02d}")
    lq = (d.month - 1) // 3  # quý gần nhất đã kết thúc
    if lq:
        kys.insert(0, f"{d.year}-Q{lq}")  # công bố quý trước để trang mở mặc định ở tháng mới nhất
    await _sample_phuc_vu(tenant_id, kys)
    await _sample_more_cases(tenant_id, users)
    u = await _user(users.get("chutich"))
    async with admin_sessionmaker()() as a:
        for ky in kys:
            snap = await build_snapshot(tenant_id, ky)
            if not snap["thong_ke"]["da_xac_nhan"]:
                continue
            a.add(CongBo(tenant_id=tenant_id, ky=ky, du_lieu=snap, nguoi_cong_bo_id=u.id if u else None,
                         nguoi_cong_bo_ten=u.ho_ten if u else "", is_sample=True))
        await a.commit()


async def _sample_phuc_vu(tenant_id: int, kys: list[str]) -> None:
    """Điểm Bộ chỉ số phục vụ người dân minh họa cho các tháng (không ghi đè số đơn vị đã nhập)."""
    import random

    from app.cong_khai.service import PHUC_VU_MAC_DINH

    months = sorted({k for k in kys if len(k) == 7 and "Q" not in k})
    if not months:
        return
    y, m = int(months[-1][:4]), int(months[-1][5:7])
    allm = [f"{y if m - i > 0 else y - 1}-{(m - i - 1) % 12 + 1:02d}" for i in range(9, -1, -1)]
    rnd = random.Random(tenant_id)
    async with admin_sessionmaker()() as a:
        t = await a.get(Tenant, tenant_id)
        data = dict((t.config or {}).get("chi_so_phuc_vu") or {})
        for i, k in enumerate(allm):
            if k in data:
                continue
            base = 0.84 + i * 0.012
            data[k] = {"tieu_chi": [{"ten": ten, "diem": round(min(td, td * (base + rnd.uniform(-0.04, 0.05))), 2), "toi_da": td} for ten, td in PHUC_VU_MAC_DINH],
                       "xep_hang": max(1, 30 - i * 2 - rnd.randint(0, 3)), "tong_don_vi": 99, "minh_hoa": True}
        t.config = {**(t.config or {}), "chi_so_phuc_vu": data}
        await a.commit()


async def _sample_more_cases(tenant_id: int, users: dict[str, int]) -> None:
    """Giao thêm hồ sơ theo dõi minh họa cho nhiều đơn vị (đủ trạng thái) để demo chuyên mục Chỉ đạo – điều hành."""
    from datetime import timedelta

    from app.alerts.models import Alert, FollowUpCase
    from app.core.db import tenant_session

    plan = [("Phòng Kinh tế, Hạ tầng và Đô thị", "hoan_thanh", -10), ("Phòng Kinh tế, Hạ tầng và Đô thị", "dang_xu_ly", 6),
            ("Văn phòng HĐND và UBND", "hoan_thanh", -5), ("Văn phòng HĐND và UBND", "da_giao", -3),
            ("Phòng Văn hóa – Xã hội", "hoan_thanh", -8), ("Phòng Văn hóa – Xã hội", "dang_xu_ly", 4),
            ("Bộ phận Một cửa", "hoan_thanh", -2), ("Công an phường", "dang_xu_ly", -4), ("Ban Quản lý dự án", "hoan_thanh", -6),
            ("Ban Quản lý dự án", "da_giao", 9), ("Bộ phận Tài chính – Kế toán", "hoan_thanh", -12)]
    today = date.today()
    async with tenant_session([tenant_id]) as ts:
        n = len(list((await ts.execute(select(FollowUpCase.id).where(FollowUpCase.tenant_id == tenant_id))).scalars()))
        if n >= 6:
            return
        free = list((await ts.execute(select(Alert).where(Alert.tenant_id == tenant_id, Alert.trang_thai == "moi").order_by(Alert.id))).scalars())
        for a, (dv, tt, han) in zip(free, plan, strict=False):
            a.trang_thai = tt
            ts.add(FollowUpCase(tenant_id=tenant_id, alert_id=a.id, co_quan_xu_ly=dv, nguoi_phu_trach="", han=today + timedelta(days=han),
                                chi_dao="Xử lý, báo cáo kết quả theo thẩm quyền", trang_thai=tt,
                                ket_qua="Đã xử lý xong, báo cáo UBND phường" if tt == "hoan_thanh" else "",
                                nguoi_giao_id=users.get("chutich") or 0, lich_su=[], is_sample=True))
        await ts.commit()


async def _user(uid: int | None):  # noqa: ANN202
    if uid is None:
        return None
    async with admin_sessionmaker()() as a:
        return await a.get(User, uid)


async def _sample_alerts(tenant_id: int, users: dict[str, int]) -> None:
    """Chạy quy tắc cảnh báo trên dữ liệu minh họa và giao sẵn 2 hồ sơ theo dõi để demo luồng chỉ đạo."""
    from datetime import date, timedelta

    from app.alerts.engine import run_rules
    from app.alerts.models import Alert, FollowUpCase
    from app.core.db import tenant_session
    from seeds.sample.ho_so import P

    async with tenant_session([tenant_id]) as ts:
        alerts = await run_rules(ts, tenant_id)
        for a in alerts:
            a.is_sample = True
        await ts.flush()
        today = date.today()
        picks = {a.rule_ma: a for a in alerts}
        for ma, co_quan, nguoi, tt, nn, hd in [
            ("NS_THU_NGUY_CO_KY", "Phòng Kinh tế, Hạ tầng và Đô thị", "Phạm Thu Dung", "dang_xu_ly",
             "Phiên đấu giá quyền sử dụng đất quý III lùi sang tháng 12", "Phối hợp Trung tâm Phát triển quỹ đất đẩy nhanh hồ sơ đấu giá"),
            ("DA_QUA_HAN_MOC", "Phòng Kinh tế, Hạ tầng và Đô thị", "Nguyễn Văn An", "da_giao", "", ""),
        ]:
            a = picks.get(ma)
            if a:
                a.trang_thai = tt
                ts.add(FollowUpCase(tenant_id=tenant_id, alert_id=a.id, co_quan_xu_ly=co_quan, nguoi_phu_trach=P.nguoi(nguoi), han=today + timedelta(days=5),
                                    chi_dao="Báo cáo nguyên nhân và giải pháp tại giao ban tuần", trang_thai=tt, nguyen_nhan=nn, hanh_dong=hd,
                                    nguoi_giao_id=users.get("chutich") or 0, lich_su=[], is_sample=True))
        await ts.flush()
        # Gắn văn bản chỉ đạo minh họa với các nhiệm vụ vừa giao
        from app.van_ban.models import VanBan

        cases = list((await ts.execute(select(FollowUpCase.id).where(FollowUpCase.tenant_id == tenant_id))).scalars())
        for vb in (await ts.execute(select(VanBan).where(VanBan.tenant_id == tenant_id, VanBan.is_sample.is_(True)))).scalars():
            if vb.nhiem_vu_ids == ["__gan__"]:
                vb.nhiem_vu_ids = cases
        await _sample_messages(ts, tenant_id, users, picks)
        await ts.commit()
        await _sample_noti(ts, tenant_id, users, picks)


async def _sample_messages(ts, tenant_id: int, users: dict, picks: dict) -> None:  # noqa: ANN001
    """Trao đổi nội bộ minh họa gắn với cảnh báo thu ngân sách chậm, và một trao đổi trực tiếp."""
    from datetime import UTC, datetime, timedelta

    from app.tin_nhan.models import HoiThoai, ThanhVien, TinNhan

    ct, kt, xn, cb = (users.get(k) for k in ("chutich", "ketoan", "xacnhan", "canbo1"))
    a = picks.get("NS_THU_NGUY_CO_KY")
    if not (ct and kt and xn):
        return
    now = datetime.now(UTC)
    threads = []
    if a is not None:
        threads.append((HoiThoai(tenant_id=tenant_id, tieu_de=a.tieu_de[:300], loai="viec", lien_ket_loai="canh_bao", lien_ket_id=a.id,
                                 lien_ket_ten=a.tieu_de[:500], lien_ket_url=f"/canh-bao?id={a.id}", tao_boi=ct, is_sample=True), [ct, kt, xn], [
            (ct, "Thu tiền sử dụng đất đang chậm so với tiến độ kỳ. Đề nghị kế toán báo cáo nguyên nhân và dự kiến số thu tháng 11.", 26),
            (kt, "Báo cáo Chủ tịch: phiên đấu giá quý III lùi sang tháng 12 nên chưa ghi thu. Em đang phối hợp Trung tâm Phát triển quỹ đất.", 25),
            (xn, "Phòng Kinh tế sẽ rà lại hồ sơ đấu giá, báo cáo tại giao ban thứ Hai.", 24),
            (ct, "Đồng ý. Gửi kèm kế hoạch thu cập nhật trước thứ Sáu.", 2),
        ]))
    if cb:
        threads.append((HoiThoai(tenant_id=tenant_id, tieu_de="", loai="truc_tiep", tao_boi=xn, is_sample=True), [xn, cb], [
            (xn, "Số liệu tỷ lệ BHYT quý III đã có từ BHXH chưa em?", 5),
            (cb, "Dạ BHXH gửi rồi ạ, em đã nhập, đang chờ anh xác nhận.", 4),
        ]))
    for h, mem, msgs in threads:
        ts.add(h)
        await ts.flush()
        last = 0
        for who, text, hours in msgs:
            m = TinNhan(tenant_id=tenant_id, hoi_thoai_id=h.id, nguoi_gui_id=who, noi_dung=text, gui_luc=now - timedelta(hours=hours), is_sample=True)
            ts.add(m)
            await ts.flush()
            last = m.id
        h.cap_nhat_luc = now - timedelta(hours=msgs[-1][2])
        for uid in mem:  # người gửi tin cuối đã đọc; người khác còn tin chưa đọc
            ts.add(ThanhVien(tenant_id=tenant_id, hoi_thoai_id=h.id, user_id=uid, doc_den=last if uid == msgs[-1][0] else 0, is_sample=True))


async def _sample_noti(ts, tenant_id: int, users: dict, picks: dict) -> None:  # noqa: ANN001
    """Thông báo minh họa cho từng vai trò (chuông)."""
    from datetime import UTC, datetime, timedelta

    from app.noti.models import Noti

    now = datetime.now(UTC)
    a = picks.get("NS_THU_NGUY_CO_KY") or next(iter(picks.values()), None)
    link = f"/canh-bao?id={a.id}" if a else "/canh-bao"
    rows = {
        "chutich": [("canh_bao", "3 cảnh báo mới", "Tiền sử dụng đất chậm tiến độ; giải ngân dự án chậm lịch vốn; chỉ tiêu BHYT có nguy cơ", "/canh-bao", "quan_trong", 1, False),
                    ("cho_xac_nhan", "Phản ánh PA-2026-9014 báo cáo hoàn thành, chờ bạn xác nhận", "Đã xử lý xong, hiện trường đã được khắc phục", "/phan-anh", "quan_trong", 3, False),
                    ("tin_nhan", "Phạm Thu Dung · Tiền sử dụng đất chậm tiến độ", "Báo cáo Chủ tịch: phiên đấu giá quý III lùi sang tháng 12…", "/tin-nhan", "thuong", 25, True)],
        "ketoan": [("giao_viec", f"Bạn được giao xử lý: {a.tieu_de if a else 'cảnh báo thu ngân sách'}", "Hạn trong 5 ngày. Báo cáo nguyên nhân và giải pháp tại giao ban tuần", link, "quan_trong", 2, False),
                   ("cong_van", "Lê Minh Châu gửi công văn số 187/TB-UBND", "Kết luận giao ban về thu ngân sách và giải ngân vốn đầu tư công.", "/van-ban", "khan", 4, False)],
        "xacnhan": [("cho_xac_nhan", "Số liệu chờ xác nhận: Tỷ lệ dân số tham gia BHYT", "Kỳ 2026-Q3: 99,2 %", "/nhap-lieu", "thuong", 1, False),
                    ("ket_qua", "Nhiệm vụ đã hoàn thành: Đèn chiếu sáng công cộng hỏng cả tuyến", "Đã thay 12 bộ đèn", "/canh-bao", "thuong", 30, True)],
        "canbo1": [("tu_choi", "Số liệu bị từ chối: Thu gom, xử lý rác thải sinh hoạt kỳ 2026-10", "Lý do: thiếu biên bản xác nhận của đơn vị thu gom", "/nhap-lieu", "quan_trong", 2, False),
                   ("giao_viec", "Bạn được giao xử lý phản ánh PA-2026-9002: Vỡ đường ống cấp nước", "Hạn hôm nay. Phối hợp công ty cấp nước", "/phan-anh", "khan", 1, False)],
        "qtphuong": [("thong_bao", "Tập huấn sử dụng hệ thống điều hành số", "Chiều thứ Tư tại hội trường", "/lich-cong-tac", "thuong", 6, False)],
    }
    for key, items in rows.items():
        uid = users.get(key)
        if not uid:
            continue
        for loai, td, nd, lk, muc, hours, read in items:
            ts.add(Noti(tenant_id=tenant_id, user_id=uid, loai=loai, tieu_de=td[:300], noi_dung=nd, lien_ket=lk, muc_do=muc,
                        tao_luc=now - timedelta(hours=hours), da_doc_luc=(now - timedelta(hours=hours - 1)) if read else None, is_sample=True))
    await ts.commit()


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


# Vai trò kịch bản minh họa → cách chọn tài khoản thật của đơn vị
async def seed_sample_for(tenant_id: int) -> dict:
    """Nạp dữ liệu minh họa cho một đơn vị bất kỳ (dùng từ màn quản trị nền tảng)."""
    from seeds.sample import ho_so

    import_models()
    async with admin_sessionmaker()() as s:
        t = await s.get(Tenant, tenant_id)
        if t is None or t.cap not in ("xa", "phuong"):
            raise ValueError("Chỉ nạp dữ liệu minh họa cho xã/phường")
        us = list((await s.execute(select(User).where(User.tenant_id == tenant_id, User.trang_thai == "hoat_dong").order_by(User.id))).scalars())
        gs = list((await s.execute(select(Grant).where(Grant.user_id.in_([u.id for u in us])))).scalars()) if us else []
        roles = {u.id: {g.role for g in gs if g.user_id == u.id} for u in us}
        nhom = {u.id: {n for g in gs if g.user_id == u.id for n in (g.nhom_du_lieu or [])} for u in us}
        pick = lambda role, cond=lambda _u: True, skip=(): next((u for u in us if role in roles[u.id] and cond(u) and u.id not in skip), None)  # noqa: E731
        lanh_dao = [u for u in us if "lanh_dao" in roles[u.id]]
        chosen = {
            "chutich": lanh_dao[0] if lanh_dao else None, "bithu": lanh_dao[1] if len(lanh_dao) > 1 else None,
            "xacnhan": pick("xac_nhan", lambda u: "ngan_sach" not in nhom[u.id]) or pick("xac_nhan"),
            "ketoan": pick("xac_nhan", lambda u: "ngan_sach" in nhom[u.id]) or pick("xac_nhan"),
            "canbo1": pick("nhap_lieu") or pick("xac_nhan") or (lanh_dao[0] if lanh_dao else None),
            "qtphuong": pick("quan_tri_don_vi"),
        }
        ids = {k: u.id for k, u in chosen.items() if u}
        ho_so.cho_don_vi(t.ma_dvhc, t.ten, t.config or {}, {k: u.username for k, u in chosen.items() if u})
        await _seed_sample(s, tenant_id, ids)
        n = 0
        for table in Base.metadata.sorted_tables:
            if "is_sample" in table.c and "tenant_id" in table.c:
                n += (await s.execute(text(f'SELECT count(*) FROM "{table.name}" WHERE tenant_id = :t AND is_sample'), {"t": tenant_id})).scalar() or 0
        return {"so_ban_ghi": n, "tai_khoan": {k: u.username for k, u in chosen.items() if u}}


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
            await seed_tenant("nenh", with_sample=True)

        asyncio.run(_demo())
    else:
        print(__doc__)
        sys.exit(1)
    print("Xong")


if __name__ == "__main__":
    main()
