from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, tenant_db
from app.catalog.models import Indicator
from app.core.periods import parse_ky
from app.core.principal import CurrentUser
from app.indicators.models import IndicatorValue
from app.indicators.service import _resolve, _rows, align, card, completeness

router = APIRouter(prefix="/api", tags=["chi-tieu"])


def _default_ky() -> str:
    return date.today().strftime("%Y-%m")


def _check(user: CurrentUser, ind: Indicator) -> None:
    if not user.can("doc", ind.nhom):
        raise HTTPException(404, "Không tìm thấy chỉ tiêu")


@router.get("/indicators")
async def list_cards(
    nhom: str | None = None, phan_he: str | None = None, bo: str | None = None, ky: str | None = None,
    s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    q = select(Indicator).where(Indicator.tenant_id == s.info["tenant_id"]).order_by(Indicator.ma_chi_tieu)
    if nhom:
        q = q.where(Indicator.nhom == nhom)
    if phan_he:
        q = q.where(Indicator.phan_he == phan_he)
    inds = [i for i in (await s.execute(q)).scalars() if user.can("doc", i.nhom) and (not bo or bo in (i.bo or []))]
    ky = ky or _default_ky()
    return [await card(s, i, ky) for i in inds]


async def _by_code(s: AsyncSession, ma: str) -> Indicator:
    ind = (await s.execute(select(Indicator).where(Indicator.tenant_id == s.info["tenant_id"], Indicator.ma_chi_tieu == ma))).scalar()
    if ind is None:
        raise HTTPException(404, "Không tìm thấy chỉ tiêu")
    return ind


@router.get("/indicators/values/{value_id}")
async def get_value(value_id: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    v = await s.get(IndicatorValue, value_id)
    if v is None or v.tenant_id != s.info["tenant_id"]:
        raise HTTPException(404, "Không tìm thấy số liệu")
    _check(user, await s.get(Indicator, v.indicator_id))
    return {"id": v.id, "ky": v.ky_bao_cao, "gia_tri": v.gia_tri, "trang_thai": v.trang_thai, "version": v.version}


@router.get("/indicators/{ma}")
async def get_card(ma: str, ky: str | None = None, s: AsyncSession = Depends(tenant_db),
                   user: CurrentUser = Depends(get_current_user)) -> dict:
    ind = await _by_code(s, ma)
    _check(user, ind)
    c = await card(s, ind, ky or _default_ky())
    c["metadata"] = {
        "dinh_nghia": ind.dinh_nghia, "cong_thuc": ind.cong_thuc, "pham_vi_dia_ban": ind.pham_vi_dia_ban,
        "don_vi_chu_quan": ind.don_vi_chu_quan, "ky_cap_nhat": ind.ky_cap_nhat, "nguon_mac_dinh": ind.nguon_mac_dinh,
        "dinh_dang": ind.dinh_dang, "phan_loai_thong_tin": ind.phan_loai_thong_tin, "ghi_chu": ind.ghi_chu,
        "can_minh_chung": ind.can_minh_chung,
    }
    versions = list((await s.execute(
        select(IndicatorValue).where(IndicatorValue.indicator_id == ind.id, IndicatorValue.ky_bao_cao == c["ky"])
        .order_by(IndicatorValue.id.desc())
    )).scalars())
    c["lich_su"] = [{"id": v.id, "version": v.version, "nguon_loai": v.nguon_loai, "gia_tri": v.gia_tri, "trang_thai": v.trang_thai,
                     "nguoi_xac_nhan": v.nguoi_xac_nhan_ten, "ly_do": v.ly_do, "thoi_diem_dong_bo": v.thoi_diem_dong_bo}
                    for v in versions]
    return c


@router.get("/indicators/{ma}/series")
async def series(ma: str, tu: str, den: str, s: AsyncSession = Depends(tenant_db),
                 user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    from app.core.num import num
    from app.core.periods import prev
    from app.indicators.service import plan_for

    ind = await _by_code(s, ma)
    _check(user, ind)
    start, p = align(parse_ky(tu), ind.ky_cap_nhat), align(parse_ky(den), ind.ky_cap_nhat)
    out: list[dict] = []
    while p >= start and len(out) < 240:
        v, state, _ = _resolve(ind, await _rows(s, ind.id, str(p), ind.scope))
        out.append({"ky": str(p), "gia_tri": num(v.gia_tri) if v else None, "data_state": state,
                    "ke_hoach": num(await plan_for(s, ind.id, str(p), ind.luy_ke))})
        p = prev(p)
    return list(reversed(out))


@router.get("/completeness")
async def get_completeness(nhom: str, ky: str = Query(default_factory=_default_ky), s: AsyncSession = Depends(tenant_db),
                           user: CurrentUser = Depends(get_current_user)) -> dict:
    if not user.can("doc", nhom):
        raise HTTPException(403, "Bạn không có quyền xem nhóm dữ liệu này")
    return await completeness(s, s.info["tenant_id"], nhom, ky)
