from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import require, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.services_pakn.models import AdminServiceStat
from app.services_pakn.service import due_soon, pakn_summary, tthc_summary

router = APIRouter(prefix="/api", tags=["hanh-chinh-cong"])
DOC = require("doc", "tthc_pakn")


def _tu() -> date:
    return date.today().replace(day=1) - timedelta(days=60)


@router.get("/tthc/summary")
async def tthc(tu: date = Query(default_factory=_tu), den: date = Query(default_factory=date.today), group: str = "thang",
               bo_phan: str | None = None, s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> dict:
    if group not in ("ngay", "tuan", "thang"):
        raise HTTPException(422, "Nhóm theo ngày, tuần hoặc tháng")
    return jsonable(await tthc_summary(s, s.info["tenant_id"], tu, den, group, bo_phan))


class TthcIn(BaseModel):
    ngay: date
    bo_phan: str = Field(min_length=1)
    linh_vuc: str = ""
    tiep_nhan: int = Field(ge=0)
    giai_quyet: int = Field(ge=0)
    dung_han: int = Field(ge=0)
    qua_han: int = Field(ge=0)
    truc_tuyen: int = Field(ge=0)


@router.post("/tthc/bieu-mau", status_code=201)
async def tthc_form(body: TthcIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(require("nhap", "tthc_pakn"))) -> dict:
    """Biểu mẫu động thay luồng Cổng DVCQG (gián đoạn từ 01/6/2026) — số liệu tạm thời chờ xác nhận."""
    if body.giai_quyet > body.tiep_nhan:
        raise HTTPException(422, "Số đã giải quyết không được lớn hơn số tiếp nhận")
    if body.dung_han + body.qua_han > body.giai_quyet:
        raise HTTPException(422, "Số đúng hạn cộng quá hạn không được lớn hơn số đã giải quyết")
    if body.truc_tuyen > body.tiep_nhan:
        raise HTTPException(422, "Số hồ sơ trực tuyến không được lớn hơn số tiếp nhận")
    row = AdminServiceStat(tenant_id=s.info["tenant_id"], nguon="bieu_mau", trang_thai="tam_thoi", nguoi_nhap_id=user.id, **body.model_dump())
    s.add(row)
    await s.commit()
    out = {"id": row.id, **body.model_dump(mode="json"), "nguon": row.nguon, "trang_thai": row.trang_thai}
    await record_change(user, row.tenant_id, f"tthc:{row.id}:nhap", None, out)
    return out


@router.get("/pakn/summary")
async def pakn(tu: date = Query(default_factory=_tu), den: date = Query(default_factory=date.today),
               s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> dict:
    return jsonable(await pakn_summary(s, s.info["tenant_id"], tu, den, date.today()))


@router.get("/pakn/can-don-doc")
async def pakn_urge(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> list:
    return jsonable(await due_soon(s, s.info["tenant_id"], date.today()))
