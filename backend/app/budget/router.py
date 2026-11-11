from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require, tenant_db
from app.budget.service import summary
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.platform.models import SharedCatalog

router = APIRouter(prefix="/api/budget", tags=["ngan-sach"])


def _last_month() -> str:
    d = date.today().replace(day=1)
    m = d.month - 1 or 12
    return f"{d.year - (d.month == 1)}-{m:02d}"


@router.get("/summary")
async def budget_summary(nam: int | None = None, ky: str = Query(default_factory=_last_month),
                         s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(require("doc", "ngan_sach"))) -> dict:
    ten = {c.ma: c.ten for c in (await s.execute(select(SharedCatalog).where(
        SharedCatalog.loai.in_(["nhom_thu", "nhom_chi", "nhiem_vu_chi"])))).scalars()}
    return jsonable(await summary(s, s.info["tenant_id"], nam or int(ky[:4]), ky, ten))
