"""Vòng đời số liệu: nhập (tạm thời) → xác nhận / từ chối; sửa số đã xác nhận tạo phiên bản mới."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, tenant_db
from app.auth.models import User
from app.catalog.models import Indicator
from app.core.db import admin_sessionmaker
from app.core.num import num
from app.core.principal import CurrentUser
from app.files.router import keys_exist
from app.indicators.models import IndicatorValue
from app.indicators.service import create_value

router = APIRouter(prefix="/api", tags=["xac-nhan-so-lieu"])


class ValueIn(BaseModel):
    ky_bao_cao: str
    gia_tri: str | float | None = None
    du_bao: str | float | None = None
    nguon: str = ""
    don_vi_cung_cap: str = ""
    thoi_diem_chot: str = ""
    nguon_loai: Literal["phuong", "chuyen_nganh"] = "phuong"
    scope: str | None = None
    ly_do: str | None = None
    minh_chung_keys: list[str] = []


def value_out(v: IndicatorValue, ind: Indicator | None = None) -> dict:
    return {
        "id": v.id, "indicator_id": v.indicator_id, "ma": ind.ma_chi_tieu if ind else None, "ten": ind.ten if ind else None,
        "nhom": ind.nhom if ind else None, "don_vi": ind.don_vi_do if ind else None,
        "ky_bao_cao": v.ky_bao_cao, "gia_tri": num(v.gia_tri), "du_bao": num(v.du_bao), "nguon": v.nguon,
        "nguon_loai": v.nguon_loai, "don_vi_cung_cap": v.don_vi_cung_cap, "thoi_diem_chot": v.thoi_diem_chot,
        "trang_thai": v.trang_thai, "version": v.version, "ly_do": v.ly_do, "minh_chung_keys": v.minh_chung_keys,
        "nguoi_nhap_id": v.nguoi_nhap_id, "is_sample": v.is_sample,
    }


async def _ind_by_code(s: AsyncSession, ma: str) -> Indicator:
    ind = (await s.execute(select(Indicator).where(Indicator.tenant_id == s.info["tenant_id"], Indicator.ma_chi_tieu == ma))).scalar()
    if ind is None:
        raise HTTPException(404, "Không tìm thấy chỉ tiêu")
    return ind


@router.post("/indicators/{ma}/values", status_code=201)
async def submit(ma: str, body: ValueIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    ind = await _ind_by_code(s, ma)
    if not user.can("nhap", ind.nhom):
        raise HTTPException(403, "Bạn không có quyền nhập số liệu nhóm này")
    if not await keys_exist(s, body.minh_chung_keys):
        raise HTTPException(422, "Tệp minh chứng không tồn tại")
    from app.indicators.service import check_period

    ky = check_period(ind, body.ky_bao_cao)
    has_confirmed = (await s.execute(select(IndicatorValue.id).where(
        IndicatorValue.indicator_id == ind.id, IndicatorValue.ky_bao_cao == ky,
        IndicatorValue.nguon_loai == body.nguon_loai, IndicatorValue.trang_thai == "da_xac_nhan",
    ))).first()
    if has_confirmed and not (body.ly_do or "").strip():
        raise HTTPException(422, "Sửa số đã xác nhận phải ghi lý do")
    v = await create_value(s, user, ind.id, body.model_dump())
    await s.commit()
    await record_change(user, s.info["tenant_id"], f"so_lieu:{v.id}:nhap", None, value_out(v) | {"thoi_diem_chot": str(v.thoi_diem_chot)})
    from app.noti.service import notify, users_with

    tid = s.info["tenant_id"]
    await notify(s, tid, await users_with(tid, duyet=ind.nhom), "cho_xac_nhan", f"Số liệu chờ xác nhận: {ind.ten}",
                 f"Kỳ {ky}: {body.gia_tri if body.gia_tri is not None else 'chưa có giá trị'} {ind.don_vi_do}", "/nhap-lieu", "thuong",
                 f"cho_xn:{ind.id}:{ky}", bo_qua=user.id)
    return value_out(v, ind)


async def _load_for_review(s: AsyncSession, user: CurrentUser, value_id: int) -> tuple[IndicatorValue, Indicator]:
    v = await s.get(IndicatorValue, value_id)
    if v is None:
        raise HTTPException(404, "Không tìm thấy số liệu")
    ind = await s.get(Indicator, v.indicator_id)
    if not user.can("duyet", ind.nhom):
        raise HTTPException(403, "Bạn không có quyền xác nhận số liệu nhóm này")
    if v.nguoi_nhap_id == user.id:
        raise HTTPException(403, "Người nhập không được tự xác nhận")
    if v.trang_thai != "tam_thoi":
        raise HTTPException(409, "Số liệu không ở trạng thái chờ xác nhận")
    return v, ind


@router.post("/values/{value_id}/confirm")
async def confirm(value_id: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    v, ind = await _load_for_review(s, user, value_id)
    if ind.can_minh_chung and not v.minh_chung_keys:
        raise HTTPException(422, "Chỉ tiêu này cần có minh chứng trước khi xác nhận")
    async with admin_sessionmaker()() as adm:
        u = await adm.get(User, user.id)
    v.trang_thai = "da_xac_nhan"
    v.nguoi_xac_nhan_id = user.id
    v.nguoi_xac_nhan_ten = f"{u.chuc_danh} {u.ho_ten}".strip() if u else user.username
    v.ngay_xac_nhan = datetime.now(UTC)
    await s.commit()
    await record_change(user, s.info["tenant_id"], f"so_lieu:{v.id}:xac_nhan", {"trang_thai": "tam_thoi"},
                        {"trang_thai": "da_xac_nhan", "gia_tri": num(v.gia_tri), "nguoi_xac_nhan": v.nguoi_xac_nhan_ten})
    from app.noti.service import mark_read_key

    await mark_read_key(s, user.id, f"cho_xn:{ind.id}:{v.ky_bao_cao}")
    await s.commit()
    from app.events import emit

    await emit("value_confirmed", tenant_id=s.info["tenant_id"], indicator_id=ind.id)
    return value_out(v, ind)


class RejectIn(BaseModel):
    ly_do: str


@router.post("/values/{value_id}/reject")
async def reject(value_id: int, body: RejectIn, s: AsyncSession = Depends(tenant_db),
                 user: CurrentUser = Depends(get_current_user)) -> dict:
    if not body.ly_do.strip():
        raise HTTPException(422, "Từ chối phải ghi lý do")
    v, ind = await _load_for_review(s, user, value_id)
    v.trang_thai = "tu_choi"
    v.ly_do = body.ly_do.strip()
    await s.commit()
    await record_change(user, s.info["tenant_id"], f"so_lieu:{v.id}:tu_choi", {"trang_thai": "tam_thoi"},
                        {"trang_thai": "tu_choi", "ly_do": v.ly_do})
    from app.noti.service import mark_read_key, notify

    await notify(s, s.info["tenant_id"], [v.nguoi_nhap_id or 0], "tu_choi", f"Số liệu bị từ chối: {ind.ten} kỳ {v.ky_bao_cao}", f"Lý do: {v.ly_do}",
                 f"/nhap-lieu?tab=bieu-mau&ma={ind.ma_chi_tieu}&ky={v.ky_bao_cao}", "quan_trong", bo_qua=user.id)
    await mark_read_key(s, user.id, f"cho_xn:{ind.id}:{v.ky_bao_cao}")
    await s.commit()
    return value_out(v, ind)


@router.get("/values/inbox")
async def inbox(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    rows = (await s.execute(
        select(IndicatorValue, Indicator).join(Indicator, Indicator.id == IndicatorValue.indicator_id)
        .where(IndicatorValue.trang_thai == "tam_thoi").order_by(IndicatorValue.id.desc())
    )).all()
    return [value_out(v, ind) for v, ind in rows if user.can("duyet", ind.nhom) and v.nguoi_nhap_id != user.id]


@router.get("/values/mine")
async def mine(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    rows = (await s.execute(
        select(IndicatorValue, Indicator).join(Indicator, Indicator.id == IndicatorValue.indicator_id)
        .where(IndicatorValue.nguoi_nhap_id == user.id).order_by(IndicatorValue.id.desc()).limit(200)
    )).all()
    return [value_out(v, ind) for v, ind in rows]
