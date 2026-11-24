from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.principal import CurrentUser
from app.field_reports.models import FieldReport
from app.platform.models import ResidentialGroup, Tenant
from app.platform.structure import NGUON_TIEP_NHAN, linh_vuc, phong_ban

NHOM = "tthc_pakn"
DONG = {"hoan_thanh", "tu_choi"}
TRANG_THAI = {
    "moi": "Mới tiếp nhận", "da_giao": "Đã giao xử lý", "dang_xu_ly": "Đang xử lý", "cho_xac_nhan": "Chờ xác nhận",
    "hoan_thanh": "Đã xử lý", "tu_choi": "Không thuộc thẩm quyền",
}


def can_assign(u: CurrentUser) -> bool:
    return u.can("duyet", NHOM) or u.can("duyet", "canh_bao")


def can_update(u: CurrentUser) -> bool:
    return u.can("nhap", NHOM) or u.can("nhap", "canh_bao") or can_assign(u)


def can_see_sender(u: CurrentUser) -> bool:
    return u.can("nhap", NHOM) or u.can("duyet", NHOM)


class Lookups:
    """Danh mục của đơn vị: thôn/TDP, phòng ban, lĩnh vực."""

    def __init__(self, tenant: Tenant, groups: list[ResidentialGroup]) -> None:
        cfg = tenant.config or {}
        self.cap = tenant.cap
        self.tdp = {g.id: g for g in groups}
        self.phong_ban = {p["ma"]: p for p in phong_ban(cfg, tenant.cap)}
        self.linh_vuc = {lv["ma"]: lv for lv in linh_vuc(cfg, tenant.cap)}

    def tdp_ten(self, tdp_id: int | None) -> str | None:
        g = self.tdp.get(tdp_id) if tdp_id else None
        return g.ten if g else None

    def pb_ten(self, ma: str | None) -> str | None:
        return self.phong_ban.get(ma, {}).get("ten", ma) if ma else None


async def lookups(s: AsyncSession, tid: int) -> Lookups:
    t = await s.get(Tenant, tid)
    groups = list((await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == tid).order_by(ResidentialGroup.ma_tdp))).scalars())
    return Lookups(t, groups)


def overdue_days(han: date | None, trang_thai: str, today: date) -> int | None:
    if han is None or trang_thai in DONG:
        return None
    d = (today - han).days
    return d if d > 0 else None


def report_out(r: FieldReport, lk: Lookups, today: date, *, sender: bool = False, full: bool = True) -> dict:
    out = {
        "id": r.id, "ma": r.ma, "tieu_de": r.tieu_de, "linh_vuc": r.linh_vuc, "linh_vuc_ten": lk.linh_vuc.get(r.linh_vuc, {}).get("ten", r.linh_vuc),
        "khan_cap": r.khan_cap, "tdp_id": r.tdp_id, "tdp_ten": lk.tdp_ten(r.tdp_id), "dia_chi": r.dia_chi,
        "lat": float(r.lat) if r.lat is not None else None, "lng": float(r.lng) if r.lng is not None else None,
        "co_vi_tri": r.lat is not None and r.lng is not None,
        "don_vi_phu_trach": r.don_vi_phu_trach, "don_vi_phu_trach_ten": lk.pb_ten(r.don_vi_phu_trach), "nguoi_phu_trach": r.nguoi_phu_trach,
        "han_xu_ly": r.han_xu_ly, "trang_thai": r.trang_thai, "trang_thai_ten": TRANG_THAI.get(r.trang_thai, r.trang_thai),
        "qua_han_ngay": overdue_days(r.han_xu_ly, r.trang_thai, today), "tien_do_pct": r.tien_do_pct,
        "tiep_nhan_luc": r.tiep_nhan_luc, "cap_nhat_luc": r.cap_nhat_luc, "is_sample": r.is_sample,
    }
    if full:
        out |= {"mo_ta": r.mo_ta, "nguon": r.nguon, "nguon_ten": NGUON_TIEP_NHAN.get(r.nguon, r.nguon), "anh_keys": r.anh_keys or [],
                "chi_dao": r.chi_dao, "ket_qua": r.ket_qua, "anh_ket_qua_keys": r.anh_ket_qua_keys or [], "hoan_thanh_luc": r.hoan_thanh_luc,
                "lich_su": r.lich_su or []}
        if sender:
            out |= {"nguoi_gui_ten": r.nguoi_gui_ten, "nguoi_gui_sdt": r.nguoi_gui_sdt}
    return out


async def next_code(s: AsyncSession, tid: int, today: date) -> str:
    prefix = f"PA-{today.year}-"
    n = (await s.execute(select(func.count()).select_from(FieldReport).where(FieldReport.tenant_id == tid, FieldReport.ma.like(f"{prefix}%")))).scalar() or 0
    while True:
        n += 1
        ma = f"{prefix}{n:04d}"
        if (await s.execute(select(FieldReport.id).where(FieldReport.tenant_id == tid, FieldReport.ma == ma))).scalar() is None:
            return ma


def history(r: FieldReport, user: CurrentUser, hanh_dong: str, **extra: object) -> None:
    r.lich_su = [*(r.lich_su or []), {"luc": datetime.now(UTC).isoformat(), "nguoi": user.username, "hanh_dong": hanh_dong,
                                      **{k: v for k, v in extra.items() if v not in (None, "")}}]
