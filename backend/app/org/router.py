"""Cơ cấu tổ chức, danh bạ công vụ và phân công: ai quản lý, liên hệ thế nào, đang xử lý việc gì."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models import Alert, FollowUpCase
from app.alerts.router import OPEN
from app.audit.service import record_change
from app.auth.deps import get_current_user, require, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.field_reports.models import FieldReport
from app.field_reports.service import DONG, NHOM, overdue_days
from app.org.models import OrgUnit, Staff
from app.org.service import KHOI, ensure_units
from app.platform.models import ResidentialGroup, Tenant
from app.platform.structure import dia_ban_label

router = APIRouter(prefix="/api/co-cau", tags=["co-cau-to-chuc"])
WRITE = require("duyet", "quan_tri")


def _hide_contact(user: CurrentUser) -> bool:
    return "man_hinh_tv" in user.roles


def _staff_out(x: Staff, hide: bool) -> dict:
    return {"id": x.id, "ma": x.ma, "don_vi_ma": x.don_vi_ma, "ho_ten": x.ho_ten, "chuc_vu": x.chuc_vu, "cap": x.cap,
            "dien_thoai": None if hide else x.dien_thoai, "email": None if hide else x.email, "nhiem_vu": x.nhiem_vu,
            "linh_vuc": x.linh_vuc or [], "dia_ban_ids": x.dia_ban_ids or [], "user_id": x.user_id, "thu_tu": x.thu_tu, "is_sample": x.is_sample}


def _unit_out(u: OrgUnit, hide: bool) -> dict:
    return {"id": u.id, "ma": u.ma, "ten": u.ten, "khoi": u.khoi, "khoi_ten": KHOI.get(u.khoi, u.khoi), "cap_tren_ma": u.cap_tren_ma,
            "lanh_dao_phu_trach_ma": u.lanh_dao_phu_trach_ma, "chuc_nang": u.chuc_nang, "dien_thoai": None if hide else u.dien_thoai,
            "email": None if hide else u.email, "dia_chi": u.dia_chi, "thu_tu": u.thu_tu}


async def _workload(s: AsyncSession, user: CurrentUser, tid: int, units: list[OrgUnit], staff: list[Staff]) -> tuple[dict, dict] | None:
    """Việc đang xử lý theo đơn vị và theo cán bộ (phản ánh hiện trường + nhiệm vụ chỉ đạo)."""
    if not (user.can("doc", NHOM) or user.can("doc", "canh_bao")):
        return None
    today = date.today()
    by_unit: dict[str, dict] = {u.ma: {"dang_xu_ly": 0, "qua_han": 0, "viec": []} for u in units}
    by_staff: dict[str, dict] = {x.ma: {"dang_xu_ly": 0, "qua_han": 0, "viec": []} for x in staff}
    name_to_staff = {x.ho_ten.strip().lower(): x.ma for x in staff}
    unit_by_name = {u.ten.strip().lower(): u.ma for u in units}

    def add(bucket: dict, item: dict) -> None:
        bucket["dang_xu_ly"] += 1
        bucket["qua_han"] += 1 if item["qua_han_ngay"] else 0
        if len(bucket["viec"]) < 20:
            bucket["viec"].append(item)

    if user.can("doc", NHOM):
        rows = (await s.execute(select(FieldReport).where(FieldReport.tenant_id == tid, FieldReport.trang_thai.not_in(DONG),
                                                          FieldReport.trang_thai != "moi"))).scalars()
        for r in rows:
            item = {"loai": "phan_anh", "id": r.id, "ten": r.tieu_de, "han": r.han_xu_ly, "qua_han_ngay": overdue_days(r.han_xu_ly, r.trang_thai, today),
                    "link": f"/phan-anh?id={r.id}"}
            if r.don_vi_phu_trach in by_unit:
                add(by_unit[r.don_vi_phu_trach], item)
            sm = name_to_staff.get((r.nguoi_phu_trach or "").strip().lower())
            if sm:
                add(by_staff[sm], item)
    rows = (await s.execute(select(Alert, FollowUpCase).join(FollowUpCase, FollowUpCase.alert_id == Alert.id)
                            .where(Alert.tenant_id == tid, Alert.trang_thai.in_(OPEN)))).all()
    for a, c in rows:
        if not user.can("doc", a.nhom):
            continue
        item = {"loai": "nhiem_vu", "id": a.id, "ten": a.tieu_de, "han": c.han, "qua_han_ngay": overdue_days(c.han, "dang_xu_ly", today),
                "link": f"/canh-bao?id={a.id}"}
        um = unit_by_name.get(c.co_quan_xu_ly.strip().lower())
        if um:
            add(by_unit[um], item)
        sm = name_to_staff.get(c.nguoi_phu_trach.strip().lower())
        if sm:
            add(by_staff[sm], item)
            st = next(x for x in staff if x.ma == sm)
            if not um and st.don_vi_ma in by_unit:
                add(by_unit[st.don_vi_ma], item)
    return by_unit, by_staff


@router.get("")
async def structure(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    tid = s.info["tenant_id"]
    t = await s.get(Tenant, tid)
    ten = t.ten[0].lower() + t.ten[1:] if t.ten else ""
    units = await ensure_units(s, tid, t.cap, ten)
    await s.commit()
    staff = list((await s.execute(select(Staff).where(Staff.tenant_id == tid).order_by(Staff.thu_tu, Staff.id))).scalars())
    groups = list((await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == tid).order_by(ResidentialGroup.ma_tdp))).scalars())
    hide = _hide_contact(user)
    wl = await _workload(s, user, tid, units, staff)
    u_out = [_unit_out(u, hide) | {"khoi_luong": wl[0].get(u.ma) if wl else None} for u in units]
    s_out = [_staff_out(x, hide) | {"khoi_luong": wl[1].get(x.ma) if wl else None} for x in staff]
    tdp_staff: dict[int, list[str]] = {}
    for x in staff:
        for g in x.dia_ban_ids or []:
            tdp_staff.setdefault(int(g), []).append(x.ma)
    return jsonable({
        "ten_don_vi": t.ten, "cap": t.cap, "khoi": KHOI, "don_vi": u_out, "can_bo": s_out,
        "dia_ban_label": dia_ban_label(t.cap),
        "dia_ban": [{"id": g.id, "ma": g.ma_tdp, "ten": g.ten, "nguoi_dung_dau": g.nguoi_dung_dau, "dien_thoai": None if hide else g.dien_thoai,
                     "can_bo_phu_trach": tdp_staff.get(g.id, [])} for g in groups if not g.ngung_hoat_dong],
        "co_khoi_luong": wl is not None,
    })


# ---------------- Quản trị ----------------
class UnitIn(BaseModel):
    ma: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    ten: str = Field(min_length=1, max_length=200)
    khoi: str
    cap_tren_ma: str | None = None
    lanh_dao_phu_trach_ma: str | None = None
    chuc_nang: str = ""
    dien_thoai: str | None = Field(None, max_length=30)
    email: str | None = None
    dia_chi: str | None = None
    thu_tu: int = 0


async def _units(s: AsyncSession, tid: int) -> dict[str, OrgUnit]:
    return {u.ma: u for u in (await s.execute(select(OrgUnit).where(OrgUnit.tenant_id == tid))).scalars()}


def _check_unit(body: UnitIn, units: dict[str, OrgUnit], self_ma: str | None) -> None:
    if body.khoi not in KHOI:
        raise HTTPException(422, "Khối không hợp lệ")
    if body.cap_tren_ma:
        if body.cap_tren_ma not in units or body.cap_tren_ma == self_ma:
            raise HTTPException(422, "Đơn vị cấp trên không hợp lệ")
        p, seen = units[body.cap_tren_ma], set()
        while p is not None and p.ma not in seen:  # chặn vòng lặp cây
            if p.ma == self_ma:
                raise HTTPException(422, "Không đặt đơn vị cấp dưới làm cấp trên")
            seen.add(p.ma)
            p = units.get(p.cap_tren_ma) if p.cap_tren_ma else None


def _apply_unit(u: OrgUnit, body: UnitIn) -> None:
    for k, v in body.model_dump().items():
        setattr(u, k, v.strip() if isinstance(v, str) else v)
    u.dien_thoai, u.email, u.dia_chi = u.dien_thoai or None, u.email or None, u.dia_chi or None
    u.cap_tren_ma, u.lanh_dao_phu_trach_ma = u.cap_tren_ma or None, u.lanh_dao_phu_trach_ma or None


@router.post("/don-vi", status_code=201)
async def add_unit(body: UnitIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(WRITE)) -> dict:
    tid = s.info["tenant_id"]
    units = await _units(s, tid)
    if body.ma in units:
        raise HTTPException(409, "Mã đơn vị đã tồn tại")
    _check_unit(body, units, None)
    u = OrgUnit(tenant_id=tid)
    _apply_unit(u, body)
    s.add(u)
    await s.commit()
    await record_change(user, tid, f"co_cau:don_vi:{body.ma}:tao", None, body.model_dump())
    return _unit_out(u, False)


@router.put("/don-vi/{ma}")
async def put_unit(ma: str, body: UnitIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(WRITE)) -> dict:
    tid = s.info["tenant_id"]
    units = await _units(s, tid)
    u = units.get(ma)
    if u is None:
        raise HTTPException(404, "Không tìm thấy đơn vị")
    if body.ma != ma:
        raise HTTPException(422, "Không đổi mã đơn vị")
    _check_unit(body, units, ma)
    before = _unit_out(u, False)
    _apply_unit(u, body)
    await s.commit()
    await record_change(user, tid, f"co_cau:don_vi:{ma}:sua", before, _unit_out(u, False))
    return _unit_out(u, False)


@router.delete("/don-vi/{ma}")
async def del_unit(ma: str, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(WRITE)) -> dict:
    tid = s.info["tenant_id"]
    units = await _units(s, tid)
    if ma not in units:
        raise HTTPException(404, "Không tìm thấy đơn vị")
    if any(u.cap_tren_ma == ma for u in units.values()):
        raise HTTPException(409, "Đơn vị còn đơn vị cấp dưới")
    if (await s.execute(select(Staff.id).where(Staff.tenant_id == tid, Staff.don_vi_ma == ma))).first():
        raise HTTPException(409, "Đơn vị còn cán bộ; chuyển cán bộ sang đơn vị khác trước")
    await s.delete(units[ma])
    await s.commit()
    await record_change(user, tid, f"co_cau:don_vi:{ma}:xoa", {"ma": ma}, None)
    return {"ok": True}


class StaffIn(BaseModel):
    ma: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    don_vi_ma: str
    ho_ten: str = Field(min_length=1, max_length=200)
    chuc_vu: str = Field(min_length=1, max_length=200)
    cap: str = Field("thanh_vien", pattern="^(truong|pho|thanh_vien)$")
    dien_thoai: str | None = Field(None, max_length=30)
    email: str | None = None
    nhiem_vu: str = ""
    linh_vuc: list[str] = []
    dia_ban_ids: list[int] = []
    user_id: int | None = None
    thu_tu: int = 0


async def _check_staff(s: AsyncSession, tid: int, body: StaffIn) -> None:
    if body.don_vi_ma not in await _units(s, tid):
        raise HTTPException(422, "Đơn vị công tác không có trong cơ cấu")
    if body.dia_ban_ids:
        ok = set((await s.execute(select(ResidentialGroup.id).where(ResidentialGroup.tenant_id == tid))).scalars())
        if not set(body.dia_ban_ids) <= ok:
            raise HTTPException(422, "Địa bàn phụ trách không thuộc đơn vị")


def _apply_staff(x: Staff, body: StaffIn) -> None:
    for k, v in body.model_dump().items():
        setattr(x, k, v.strip() if isinstance(v, str) else v)
    x.dien_thoai, x.email = x.dien_thoai or None, x.email or None


@router.post("/can-bo", status_code=201)
async def add_staff(body: StaffIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(WRITE)) -> dict:
    tid = s.info["tenant_id"]
    if (await s.execute(select(Staff.id).where(Staff.tenant_id == tid, Staff.ma == body.ma))).first():
        raise HTTPException(409, "Mã cán bộ đã tồn tại")
    await _check_staff(s, tid, body)
    x = Staff(tenant_id=tid)
    _apply_staff(x, body)
    s.add(x)
    await s.commit()
    await record_change(user, tid, f"co_cau:can_bo:{body.ma}:tao", None, body.model_dump())
    return _staff_out(x, False)


async def _get_staff(s: AsyncSession, tid: int, sid: int) -> Staff:
    x = await s.get(Staff, sid)
    if x is None or x.tenant_id != tid:
        raise HTTPException(404, "Không tìm thấy cán bộ")
    return x


@router.put("/can-bo/{sid}")
async def put_staff(sid: int, body: StaffIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(WRITE)) -> dict:
    tid = s.info["tenant_id"]
    x = await _get_staff(s, tid, sid)
    if body.ma != x.ma and (await s.execute(select(Staff.id).where(Staff.tenant_id == tid, Staff.ma == body.ma))).first():
        raise HTTPException(409, "Mã cán bộ đã tồn tại")
    await _check_staff(s, tid, body)
    before = _staff_out(x, False)
    _apply_staff(x, body)
    await s.commit()
    await record_change(user, tid, f"co_cau:can_bo:{sid}:sua", before, _staff_out(x, False))
    return _staff_out(x, False)


@router.delete("/can-bo/{sid}")
async def del_staff(sid: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(WRITE)) -> dict:
    tid = s.info["tenant_id"]
    x = await _get_staff(s, tid, sid)
    before = _staff_out(x, False)
    await s.delete(x)
    await s.commit()
    await record_change(user, tid, f"co_cau:can_bo:{sid}:xoa", before, None)
    return {"ok": True}
