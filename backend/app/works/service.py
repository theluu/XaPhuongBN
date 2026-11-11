from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.models import Tenant
from app.works.models import Work, WorkProgress

WEEK_GRACE = 7 + 3


async def latest(s: AsyncSession, wid: int, confirmed_only: bool = False) -> WorkProgress | None:
    q = select(WorkProgress).where(WorkProgress.work_id == wid)
    if confirmed_only:
        q = q.where(WorkProgress.trang_thai_xac_nhan == "da_xac_nhan")
    return (await s.execute(q.order_by(WorkProgress.ngay.desc(), WorkProgress.id.desc()))).scalars().first()


def prog_out(p: WorkProgress | None) -> dict | None:
    if p is None:
        return None
    cham = p.ke_hoach_pct is not None and p.thuc_te_pct is not None and p.thuc_te_pct < p.ke_hoach_pct
    return {"id": p.id, "ngay": p.ngay, "ke_hoach_pct": p.ke_hoach_pct, "thuc_te_pct": p.thuc_te_pct, "cham": cham,
            "gpmb": p.gpmb, "vuong_mac": p.vuong_mac, "can_quyet_dinh": p.can_quyet_dinh, "anh_keys": p.anh_keys,
            "minh_chung_keys": p.minh_chung_keys, "trang_thai_xac_nhan": p.trang_thai_xac_nhan}


async def work_row(s: AsyncSession, w: Work, today: date | None = None) -> dict:
    today = today or date.today()
    p = await latest(s, w.id)
    tre = (today - w.ngay_ht).days if w.ngay_ht and w.ngay_ht < today and w.trang_thai != "hoan_thanh" else None
    return {"id": w.id, "ma": w.ma_cong_trinh, "ten": w.ten, "loai": w.loai, "dia_diem": w.dia_diem, "project_id": w.project_id,
            "don_vi_thuc_hien": w.don_vi_thuc_hien, "chu_dau_tu": w.chu_dau_tu, "ngay_kc": w.ngay_kc, "ngay_ht": w.ngay_ht,
            "chat_luong": w.chat_luong, "camera_url": w.camera_url, "trang_thai": w.trang_thai, "tre_han_ngay": tre,
            "moi_nhat": prog_out(p), "lat": w.lat, "lng": w.lng, "is_sample": w.is_sample}


async def list_works(s: AsyncSession, tenant_id: int, today: date | None = None) -> list[dict]:
    rows = (await s.execute(select(Work).where(Work.tenant_id == tenant_id).order_by(Work.ma_cong_trinh))).scalars()
    return [await work_row(s, w, today) for w in rows]


def _in_bbox(lat: Decimal, lng: Decimal, bbox: list | None) -> bool:
    if not bbox:
        return True
    return float(bbox[0]) <= float(lat) <= float(bbox[2]) and float(bbox[1]) <= float(lng) <= float(bbox[3])


async def valid_points(s: AsyncSession, tenant_id: int) -> list[Work]:
    """Chỉ hiển thị trên bản đồ khi có vị trí hợp lệ (DT II.5)."""
    t = await s.get(Tenant, tenant_id)
    bbox = ((t.config or {}).get("ban_do") or {}).get("bbox") if t else None
    rows = (await s.execute(select(Work).where(Work.tenant_id == tenant_id, Work.lat.is_not(None), Work.lng.is_not(None), Work.toa_do_hop_le))).scalars()
    return [w for w in rows if _in_bbox(w.lat, w.lng, bbox)]


async def behind_schedule(s: AsyncSession, tenant_id: int, today: date) -> list[dict]:
    out = []
    for r in await list_works(s, tenant_id, today):
        m = r["moi_nhat"]
        chenh = (m["ke_hoach_pct"] - m["thuc_te_pct"]) if m and m["cham"] else None
        if chenh is not None or r["tre_han_ngay"]:
            out.append({"work_id": r["id"], "ma": r["ma"], "ten": r["ten"], "chenh_pct": chenh, "tre_han_ngay": r["tre_han_ngay"]})
    return out


async def missing_decision_dossier(s: AsyncSession, tenant_id: int) -> list[dict]:
    """Vướng mắc cần lãnh đạo quyết định nhưng chưa có hồ sơ kèm theo (DT II.5)."""
    out = []
    for w in (await s.execute(select(Work).where(Work.tenant_id == tenant_id).order_by(Work.id))).scalars():
        p = await latest(s, w.id)
        if p and p.can_quyet_dinh and not (p.minh_chung_keys or p.anh_keys):
            out.append({"work_id": w.id, "ma": w.ma_cong_trinh, "ten": w.ten, "vuong_mac": p.vuong_mac})
    return out


async def stale_works(s: AsyncSession, tenant_id: int, today: date) -> list[dict]:
    """Công trình đang thi công quá 1 tuần (+3 ngày) chưa cập nhật tiến độ."""
    out = []
    for w in (await s.execute(select(Work).where(Work.tenant_id == tenant_id, Work.trang_thai != "hoan_thanh").order_by(Work.id))).scalars():
        p = await latest(s, w.id)
        if p is None or p.ngay < today - timedelta(days=WEEK_GRACE):
            out.append({"work_id": w.id, "ma": w.ma_cong_trinh, "ten": w.ten, "lan_cap_nhat_cuoi": p.ngay if p else None})
    return out
