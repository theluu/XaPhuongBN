"""Tổng quan điều hành (Thiết kế giao diện IOC §2, §3): hàng chỉ số, danh sách việc cần xử lý, điểm trên bản đồ.

Gộp ba nguồn việc: phản ánh hiện trường, nhiệm vụ chỉ đạo (hồ sơ theo dõi đã giao), cảnh báo chưa giao.
Ưu tiên: khẩn cấp → quá hạn (lâu nhất trước) → hạn gần nhất.
"""
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models import Alert, FollowUpCase
from app.alerts.router import OPEN
from app.auth.deps import get_current_user, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.field_reports.models import FieldReport
from app.field_reports.service import DONG, NHOM, TRANG_THAI, lookups, overdue_days
from app.platform.structure import NGUON_TIEP_NHAN, dia_ban_label

router = APIRouter(prefix="/api/dieu-hanh", tags=["tong-quan-dieu-hanh"])
LOC = {"moi", "den_han", "qua_han", "canh_bao"}
TT_CASE = {"da_giao": "Đã giao xử lý", "dang_xu_ly": "Đang xử lý", "gia_han": "Gia hạn", "moi": "Chưa giao"}


def _sort_key(x: dict) -> tuple:
    return (not x["khan_cap"], -(x["qua_han_ngay"] or 0), x["han"] or "9999-12-31", -x["id"])


async def collect(s: AsyncSession, user: CurrentUser, today: date, tdp: int | None = None) -> tuple[list[dict], list[datetime]]:
    tid = s.info["tenant_id"]
    lk = await lookups(s, tid)
    items: list[dict] = []
    stamps: list[datetime] = []
    if user.can("doc", NHOM):
        stmt = select(FieldReport).where(FieldReport.tenant_id == tid, FieldReport.trang_thai.not_in(DONG))
        if tdp:
            stmt = stmt.where(FieldReport.tdp_id == tdp)
        for r in (await s.execute(stmt)).scalars():
            stamps.append(r.cap_nhat_luc)
            items.append({
                "loai": "phan_anh", "id": r.id, "ma": r.ma, "ten": r.tieu_de, "khan_cap": r.khan_cap,
                "dia_diem": r.dia_chi or lk.tdp_ten(r.tdp_id) or "", "tdp_ten": lk.tdp_ten(r.tdp_id),
                "don_vi": lk.pb_ten(r.don_vi_phu_trach), "don_vi_ma": r.don_vi_phu_trach, "nguoi_phu_trach": r.nguoi_phu_trach,
                "trang_thai": r.trang_thai, "trang_thai_ten": TRANG_THAI.get(r.trang_thai, r.trang_thai),
                "han": r.han_xu_ly.isoformat() if r.han_xu_ly else None, "qua_han_ngay": overdue_days(r.han_xu_ly, r.trang_thai, today),
                "lat": float(r.lat) if r.lat is not None else None, "lng": float(r.lng) if r.lng is not None else None,
                "linh_vuc_ten": lk.linh_vuc.get(r.linh_vuc, {}).get("ten", r.linh_vuc), "moi": r.trang_thai == "moi",
                "link": f"/phan-anh?id={r.id}",
            })
    if not tdp:  # nhiệm vụ, cảnh báo không gắn thôn/TDP
        rows = (await s.execute(select(Alert, FollowUpCase).outerjoin(FollowUpCase, FollowUpCase.alert_id == Alert.id)
                                .where(Alert.tenant_id == tid, Alert.trang_thai.in_(OPEN)))).all()
        for a, c in rows:
            if not user.can("doc", a.nhom):
                continue
            stamps.append(c.cap_nhat_luc if c else a.lan_cuoi_kiem_tra)
            han = c.han if c else None
            items.append({
                "loai": "nhiem_vu" if c else "canh_bao", "id": a.id, "ma": f"CB-{a.id}", "ten": a.tieu_de, "khan_cap": False,
                "muc_do": a.muc_do, "dia_diem": "", "tdp_ten": None, "don_vi": c.co_quan_xu_ly if c else None,
                "nguoi_phu_trach": c.nguoi_phu_trach if c else None, "trang_thai": c.trang_thai if c else a.trang_thai,
                "trang_thai_ten": TT_CASE.get(c.trang_thai if c else a.trang_thai, "Đang mở"),
                "han": han.isoformat() if han else None, "qua_han_ngay": overdue_days(han, "dang_xu_ly", today),
                "lat": None, "lng": None, "linh_vuc_ten": None, "moi": False, "link": f"/canh-bao?id={a.id}",
            })
    return items, stamps


async def whoami(s: AsyncSession, user: CurrentUser) -> dict:
    """Cán bộ gắn với tài khoản (Cơ cấu tổ chức) → tên và đơn vị để lọc "Việc của tôi"."""
    from app.auth.models import User
    from app.core.db import admin_sessionmaker
    from app.org.models import OrgUnit, Staff

    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as a:
        u = await a.get(User, user.id)
    st = (await s.execute(select(Staff).where(Staff.tenant_id == tid, Staff.user_id == user.id))).scalars().first()
    names = {n.strip().lower() for n in [u.ho_ten if u else "", st.ho_ten if st else ""] if n and n.strip()}
    unit = (await s.execute(select(OrgUnit).where(OrgUnit.tenant_id == tid, OrgUnit.ma == st.don_vi_ma))).scalar() if st else None
    # Lãnh đạo UBND/Đảng ủy/HĐND: "việc của tôi" là việc giao đích danh, không gộp cả cơ quan
    unit_ok = unit is not None and unit.khoi not in ("ubnd", "dang", "hdnd")
    return {"ten": st.ho_ten if st else (u.ho_ten if u else ""), "chuc_vu": st.chuc_vu if st else (u.chuc_danh if u else ""),
            "don_vi_ma": unit.ma if unit_ok else None, "don_vi_ten": unit.ten if unit_ok else None, "names": names}


def mine(x: dict, me: dict) -> bool:
    if (x.get("nguoi_phu_trach") or "").strip().lower() in me["names"]:
        return True
    return bool(me["don_vi_ma"]) and (x.get("don_vi_ma") == me["don_vi_ma"] or (x.get("don_vi") or "").strip().lower() == (me["don_vi_ten"] or "").lower())


@router.get("/tong-quan")
async def overview(loc: str | None = None, tdp: int | None = None, che_do: str = "lam_viec", pham_vi: str = "tat_ca",
                   s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    if loc and loc not in LOC:
        raise HTTPException(422, "Bộ lọc không hợp lệ")
    if pham_vi not in ("tat_ca", "cua_toi"):
        raise HTTPException(422, "Phạm vi không hợp lệ")
    today = date.today()
    items, stamps = await collect(s, user, today, tdp)
    me = await whoami(s, user)
    if pham_vi == "cua_toi":
        items = [x for x in items if mine(x, me)]
    iso = today.isoformat()
    chi_so = {
        "phan_anh_moi": sum(1 for x in items if x["moi"]),
        "den_han_hom_nay": sum(1 for x in items if x["han"] == iso),
        "qua_han": sum(1 for x in items if x["qua_han_ngay"]),
        "canh_bao_mo": sum(1 for x in items if x["loai"] in ("canh_bao", "nhiem_vu")),
    }
    if loc == "moi":
        items = [x for x in items if x["moi"]]
    elif loc == "den_han":
        items = [x for x in items if x["han"] == iso]
    elif loc == "qua_han":
        items = [x for x in items if x["qua_han_ngay"]]
    elif loc == "canh_bao":
        items = [x for x in items if x["loai"] in ("canh_bao", "nhiem_vu")]
    items.sort(key=_sort_key)
    tv = che_do == "tv"
    if tv:  # §3: 3–5 việc nổi bật, không thông tin cá nhân
        items = [x for x in items if x["khan_cap"] or x["qua_han_ngay"]][:5] or items[:5]
        items = [{**x, "nguoi_phu_trach": None} for x in items]
    lk = await lookups(s, s.info["tenant_id"])
    return jsonable({
        "chi_so": chi_so, "viec": items, "tong": len(items), "pham_vi": pham_vi,
        "toi": {"ten": me["ten"], "chuc_vu": me["chuc_vu"], "don_vi_ten": me["don_vi_ten"]},
        "cap_nhat_luc": datetime.now(UTC), "du_lieu_moi_nhat": max(stamps) if stamps else None,
        "bo_loc": {"dia_ban_label": dia_ban_label(lk.cap), "tdp": [{"id": g.id, "ten": g.ten} for g in lk.tdp.values() if not g.ngung_hoat_dong]},
    })


@router.get("/danh-muc")
async def catalogs(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(get_current_user)) -> dict:
    """Danh mục dùng cho biểu mẫu: thôn/TDP, phòng ban, lĩnh vực, nguồn tiếp nhận."""
    lk = await lookups(s, s.info["tenant_id"])
    return jsonable({
        "cap": lk.cap, "dia_ban_label": dia_ban_label(lk.cap),
        "dia_ban": [{"id": g.id, "ma": g.ma_tdp, "ten": g.ten, "lat": g.lat, "lng": g.lng} for g in lk.tdp.values() if not g.ngung_hoat_dong],
        "phong_ban": list(lk.phong_ban.values()), "linh_vuc": list(lk.linh_vuc.values()),
        "nguon": [{"ma": k, "ten": v} for k, v in NGUON_TIEP_NHAN.items()],
    })
