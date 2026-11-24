"""Phản ánh hiện trường (Thiết kế giao diện IOC §4): tiếp nhận → xác định địa điểm → giao → theo dõi hạn → xác nhận đã xử lý."""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, require, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.field_reports.models import FieldReport
from app.field_reports.service import (DONG, NHOM, can_assign, can_see_sender, can_update, history, lookups, next_code,
                                       overdue_days, report_out)
from app.files.router import keys_exist
from app.platform.structure import NGUON_TIEP_NHAN

router = APIRouter(prefix="/api/phan-anh", tags=["phan-anh-hien-truong"])
DOC = require("doc", NHOM)


def _coords(lat: float | None, lng: float | None) -> tuple[Decimal | None, Decimal | None]:
    if lat is None and lng is None:
        return None, None
    if lat is None or lng is None or not (8 <= lat <= 24 and 102 <= lng <= 110):
        raise HTTPException(422, "Tọa độ không hợp lệ (phải nằm trong lãnh thổ Việt Nam, đủ vĩ độ và kinh độ)")
    return Decimal(str(round(lat, 6))), Decimal(str(round(lng, 6)))


@router.get("")
async def list_reports(trang_thai: str | None = None, linh_vuc: str | None = None, tdp: int | None = None, loc: str | None = None,
                       q: str | None = None, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(DOC)) -> list:
    tid, today = s.info["tenant_id"], date.today()
    stmt = select(FieldReport).where(FieldReport.tenant_id == tid)
    if trang_thai == "dang_mo":
        stmt = stmt.where(FieldReport.trang_thai.not_in(DONG))
    elif trang_thai:
        stmt = stmt.where(FieldReport.trang_thai == trang_thai)
    if linh_vuc:
        stmt = stmt.where(FieldReport.linh_vuc == linh_vuc)
    if tdp:
        stmt = stmt.where(FieldReport.tdp_id == tdp)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(FieldReport.tieu_de.ilike(like) | FieldReport.ma.ilike(like) | FieldReport.dia_chi.ilike(like))
    rows = list((await s.execute(stmt.order_by(FieldReport.id.desc()).limit(500))).scalars())
    if loc == "qua_han":
        rows = [r for r in rows if overdue_days(r.han_xu_ly, r.trang_thai, today)]
    elif loc == "chua_vi_tri":
        rows = [r for r in rows if r.lat is None]
    lk = await lookups(s, tid)
    rows.sort(key=lambda r: (r.trang_thai in DONG, not r.khan_cap, -(overdue_days(r.han_xu_ly, r.trang_thai, today) or 0), r.han_xu_ly or date.max))
    return jsonable([report_out(r, lk, today, full=False) for r in rows])


async def _get(s: AsyncSession, rid: int) -> FieldReport:
    r = await s.get(FieldReport, rid)
    if r is None or r.tenant_id != s.info["tenant_id"]:
        raise HTTPException(404, "Không tìm thấy phản ánh")
    return r


async def _out(s: AsyncSession, r: FieldReport, user: CurrentUser) -> dict:
    lk = await lookups(s, r.tenant_id)
    out = report_out(r, lk, date.today(), sender=can_see_sender(user))
    out["quyen"] = {"giao": can_assign(user) and r.trang_thai not in DONG, "cap_nhat": can_update(user) and r.trang_thai in ("da_giao", "dang_xu_ly"),
                    "xac_nhan": can_assign(user) and r.trang_thai == "cho_xac_nhan"}
    return jsonable(out)


@router.get("/{rid}")
async def get_report(rid: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(DOC)) -> dict:
    return await _out(s, await _get(s, rid), user)


class ReportIn(BaseModel):
    tieu_de: str = Field(min_length=3, max_length=300)
    mo_ta: str = ""
    linh_vuc: str
    nguon: str = "truc_tiep"
    khan_cap: bool = False
    tdp_id: int | None = None
    dia_chi: str = ""
    lat: float | None = None
    lng: float | None = None
    anh_keys: list[str] = []
    nguoi_gui_ten: str | None = None
    nguoi_gui_sdt: str | None = Field(None, max_length=30)


@router.post("", status_code=201)
async def create_report(body: ReportIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    if not (user.can("nhap", NHOM) or can_assign(user)):
        raise HTTPException(403, "Bạn không có quyền tiếp nhận phản ánh")
    tid, today = s.info["tenant_id"], date.today()
    lk = await lookups(s, tid)
    if body.linh_vuc not in lk.linh_vuc:
        raise HTTPException(422, "Lĩnh vực không có trong danh mục của đơn vị")
    if body.nguon not in NGUON_TIEP_NHAN:
        raise HTTPException(422, "Nguồn tiếp nhận không hợp lệ")
    if body.tdp_id is not None and body.tdp_id not in lk.tdp:
        raise HTTPException(422, "Thôn/tổ dân phố không thuộc đơn vị")
    if not body.dia_chi.strip() and body.tdp_id is None and body.lat is None:
        raise HTTPException(422, "Cần ghi địa chỉ, chọn thôn/tổ dân phố hoặc vị trí trên bản đồ")
    if not await keys_exist(s, body.anh_keys):
        raise HTTPException(422, "Ảnh hiện trường chưa được tải lên")
    lat, lng = _coords(body.lat, body.lng)
    lv = lk.linh_vuc[body.linh_vuc]
    han_ngay = 1 if body.khan_cap else int(lv.get("han_ngay") or 7)
    r = FieldReport(tenant_id=tid, ma=await next_code(s, tid, today), tieu_de=body.tieu_de.strip(), mo_ta=body.mo_ta.strip(), linh_vuc=body.linh_vuc,
                    nguon=body.nguon, khan_cap=body.khan_cap, tdp_id=body.tdp_id, dia_chi=body.dia_chi.strip(), lat=lat, lng=lng,
                    anh_keys=body.anh_keys, nguoi_gui_ten=(body.nguoi_gui_ten or "").strip() or None, nguoi_gui_sdt=(body.nguoi_gui_sdt or "").strip() or None,
                    don_vi_phu_trach=lv.get("chu_tri"), han_xu_ly=today + timedelta(days=han_ngay), trang_thai="moi", nguoi_tiep_nhan_id=user.id,
                    lich_su=[], tien_do_pct=0)
    history(r, user, "tiep_nhan", nguon=body.nguon)
    s.add(r)
    await s.commit()
    await s.refresh(r)
    await record_change(user, tid, f"phan_anh:{r.id}:tiep_nhan", None, {"ma": r.ma, "linh_vuc": r.linh_vuc, "khan_cap": r.khan_cap})
    return await _out(s, r, user)


class LocateIn(BaseModel):
    tdp_id: int | None = None
    dia_chi: str | None = None
    lat: float | None = None
    lng: float | None = None


@router.patch("/{rid}/vi-tri")
async def locate(rid: int, body: LocateIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(DOC)) -> dict:
    if not can_update(user):
        raise HTTPException(403, "Bạn không có quyền cập nhật phản ánh")
    r = await _get(s, rid)
    lk = await lookups(s, r.tenant_id)
    if body.tdp_id is not None and body.tdp_id not in lk.tdp:
        raise HTTPException(422, "Thôn/tổ dân phố không thuộc đơn vị")
    before = {"lat": r.lat, "lng": r.lng, "tdp_id": r.tdp_id, "dia_chi": r.dia_chi}
    r.lat, r.lng = _coords(body.lat, body.lng)
    if body.tdp_id is not None:
        r.tdp_id = body.tdp_id
    if body.dia_chi is not None:
        r.dia_chi = body.dia_chi.strip()
    history(r, user, "xac_dinh_vi_tri")
    await s.commit()
    await s.refresh(r)
    await record_change(user, r.tenant_id, f"phan_anh:{rid}:vi_tri", jsonable(before), {"lat": body.lat, "lng": body.lng, "tdp_id": r.tdp_id})
    return await _out(s, r, user)


class AssignIn(BaseModel):
    don_vi_phu_trach: str
    nguoi_phu_trach: str = ""
    han_xu_ly: date
    chi_dao: str = ""


@router.post("/{rid}/giao")
async def assign(rid: int, body: AssignIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(DOC)) -> dict:
    if not can_assign(user):
        raise HTTPException(403, "Chỉ lãnh đạo hoặc cán bộ được phân quyền mới giao xử lý")
    r = await _get(s, rid)
    if r.trang_thai in DONG:
        raise HTTPException(409, "Phản ánh đã đóng")
    lk = await lookups(s, r.tenant_id)
    if body.don_vi_phu_trach not in lk.phong_ban:
        raise HTTPException(422, "Đơn vị phụ trách không có trong danh mục")
    if body.han_xu_ly < date.today():
        raise HTTPException(422, "Hạn xử lý không được trước ngày hôm nay")
    r.don_vi_phu_trach, r.nguoi_phu_trach, r.han_xu_ly, r.chi_dao = body.don_vi_phu_trach, body.nguoi_phu_trach.strip() or None, body.han_xu_ly, body.chi_dao.strip()
    r.trang_thai = "da_giao"
    history(r, user, "giao_xu_ly", don_vi=lk.pb_ten(body.don_vi_phu_trach), han=body.han_xu_ly.isoformat(), ghi_chu=body.chi_dao.strip())
    await s.commit()
    await s.refresh(r)
    await record_change(user, r.tenant_id, f"phan_anh:{rid}:giao", None, jsonable(body.model_dump()))
    from app.noti.service import notify, users_by_name

    await notify(s, r.tenant_id, await users_by_name(r.tenant_id, r.nguoi_phu_trach), "giao_viec", f"Bạn được giao xử lý phản ánh {r.ma}: {r.tieu_de}",
                 f"Hạn {r.han_xu_ly.strftime('%d/%m/%Y')}. {r.chi_dao or ''}".strip(), f"/phan-anh?id={rid}", "khan" if r.khan_cap else "quan_trong",
                 f"phan_anh_giao:{rid}", bo_qua=user.id)
    return await _out(s, r, user)


class ProgressIn(BaseModel):
    tien_do_pct: int | None = Field(None, ge=0, le=100)
    ghi_chu: str = ""
    ket_qua: str | None = None
    anh_ket_qua_keys: list[str] | None = None
    bao_cao_hoan_thanh: bool = False


@router.post("/{rid}/tien-do")
async def progress(rid: int, body: ProgressIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(DOC)) -> dict:
    if not can_update(user):
        raise HTTPException(403, "Bạn không có quyền cập nhật tiến độ")
    r = await _get(s, rid)
    if r.trang_thai not in ("da_giao", "dang_xu_ly"):
        raise HTTPException(409, "Chỉ cập nhật tiến độ khi phản ánh đã được giao và chưa báo cáo hoàn thành")
    if body.anh_ket_qua_keys is not None:
        if not await keys_exist(s, body.anh_ket_qua_keys):
            raise HTTPException(422, "Ảnh kết quả chưa được tải lên")
        r.anh_ket_qua_keys = body.anh_ket_qua_keys
    if body.ket_qua is not None:
        r.ket_qua = body.ket_qua.strip()
    if body.tien_do_pct is not None:
        r.tien_do_pct = body.tien_do_pct
    if body.bao_cao_hoan_thanh:
        if not r.ket_qua:
            raise HTTPException(422, "Báo cáo hoàn thành phải ghi kết quả xử lý")
        r.trang_thai, r.tien_do_pct = "cho_xac_nhan", 100
        history(r, user, "bao_cao_hoan_thanh", ghi_chu=body.ghi_chu.strip() or r.ket_qua)
    else:
        if not body.ghi_chu.strip() and body.tien_do_pct is None:
            raise HTTPException(422, "Cần ghi nội dung cập nhật hoặc tiến độ")
        r.trang_thai = "dang_xu_ly"
        history(r, user, "cap_nhat_tien_do", tien_do=r.tien_do_pct, ghi_chu=body.ghi_chu.strip())
    await s.commit()
    await s.refresh(r)
    await record_change(user, r.tenant_id, f"phan_anh:{rid}:tien_do", None, jsonable(body.model_dump()))
    if body.bao_cao_hoan_thanh:
        from sqlalchemy import select as _select

        from app.auth.models import User as _User
        from app.core.db import admin_sessionmaker as _adm
        from app.noti.service import notify

        giao = [h.get("nguoi") for h in r.lich_su or [] if h.get("hanh_dong") == "giao_xu_ly"]
        ids = []
        if giao:
            async with _adm()() as a:
                ids = list((await a.execute(_select(_User.id).where(_User.username == giao[-1], _User.tenant_id == r.tenant_id))).scalars())
        await notify(s, r.tenant_id, ids, "cho_xac_nhan", f"Phản ánh {r.ma} báo cáo hoàn thành, chờ bạn xác nhận", r.ket_qua[:300],
                     f"/phan-anh?id={rid}", "quan_trong", f"phan_anh_xn:{rid}", bo_qua=user.id)
    return await _out(s, r, user)


class ConfirmIn(BaseModel):
    dong_y: bool
    ghi_chu: str = ""


@router.post("/{rid}/xac-nhan")
async def confirm(rid: int, body: ConfirmIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(DOC)) -> dict:
    """Lãnh đạo xác nhận đã xử lý, hoặc trả lại để xử lý tiếp (bắt buộc ghi lý do)."""
    if not can_assign(user):
        raise HTTPException(403, "Chỉ lãnh đạo hoặc cán bộ được phân quyền mới xác nhận")
    r = await _get(s, rid)
    if r.trang_thai != "cho_xac_nhan":
        raise HTTPException(409, "Phản ánh chưa được báo cáo hoàn thành")
    if body.dong_y:
        r.trang_thai, r.hoan_thanh_luc = "hoan_thanh", datetime.now(UTC)
        history(r, user, "xac_nhan_hoan_thanh", ghi_chu=body.ghi_chu.strip())
    else:
        if not body.ghi_chu.strip():
            raise HTTPException(422, "Trả lại phải ghi lý do")
        r.trang_thai = "dang_xu_ly"
        history(r, user, "tra_lai", ghi_chu=body.ghi_chu.strip())
    await s.commit()
    await s.refresh(r)
    await record_change(user, r.tenant_id, f"phan_anh:{rid}:xac_nhan", None, jsonable(body.model_dump()))
    from app.noti.service import notify, users_by_name

    await notify(s, r.tenant_id, await users_by_name(r.tenant_id, r.nguoi_phu_trach), "ket_qua" if body.dong_y else "tu_choi",
                 f"Phản ánh {r.ma} {'đã được xác nhận hoàn thành' if body.dong_y else 'bị trả lại, cần xử lý tiếp'}", body.ghi_chu.strip(),
                 f"/phan-anh?id={rid}", "thuong" if body.dong_y else "quan_trong", bo_qua=user.id)
    return await _out(s, r, user)


class RejectIn(BaseModel):
    ly_do: str


@router.post("/{rid}/tu-choi")
async def reject(rid: int, body: RejectIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(DOC)) -> dict:
    """Không thuộc thẩm quyền / trùng lặp: đóng phản ánh, bắt buộc ghi lý do để trả lời người dân."""
    if not can_assign(user):
        raise HTTPException(403, "Bạn không có quyền đóng phản ánh")
    if not body.ly_do.strip():
        raise HTTPException(422, "Cần ghi lý do")
    r = await _get(s, rid)
    if r.trang_thai in DONG:
        raise HTTPException(409, "Phản ánh đã đóng")
    r.trang_thai, r.ket_qua, r.hoan_thanh_luc = "tu_choi", body.ly_do.strip(), datetime.now(UTC)
    history(r, user, "tu_choi", ghi_chu=body.ly_do.strip())
    await s.commit()
    await s.refresh(r)
    await record_change(user, r.tenant_id, f"phan_anh:{rid}:tu_choi", None, {"ly_do": body.ly_do})
    return await _out(s, r, user)
