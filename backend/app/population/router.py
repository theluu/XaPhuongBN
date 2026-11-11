from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.platform.models import Tenant
from app.population.service import population

router = APIRouter(prefix="/api/population", tags=["dan-cu"])


@router.get("")
async def get_population(ky: str = Query(default_factory=lambda: date.today().strftime("%Y-%m")), tdp: int | None = None,
                         s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(require("doc", "dan_cu"))) -> dict:
    from app.core.db import admin_sessionmaker

    async with admin_sessionmaker()() as adm:
        t = await adm.get(Tenant, s.info["tenant_id"])
    allow = bool((t.config or {}).get("cho_phep_theo_tdp"))
    if tdp is not None and not allow:
        raise HTTPException(403, "Nguồn dữ liệu chưa cho phép thống kê theo tổ dân phố")
    return jsonable(await population(s, s.info["tenant_id"], ky, allow))
