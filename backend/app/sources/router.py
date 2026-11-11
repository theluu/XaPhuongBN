from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require, tenant_db
from app.core.db import admin_sessionmaker
from app.core.principal import CurrentUser
from app.sources.models import DataSource
from app.sources.service import module_status, run_sync, source_out

router = APIRouter(prefix="/api", tags=["nguon-du-lieu"])


@router.get("/sources")
async def list_sources(s: AsyncSession = Depends(tenant_db)) -> list[dict]:
    rows = (await s.execute(select(DataSource).order_by(DataSource.nhom_du_lieu, DataSource.ma))).scalars()
    return [source_out(x) for x in rows]


@router.get("/modules")
async def modules(s: AsyncSession = Depends(tenant_db)) -> dict[str, str]:
    return await module_status(s, s.info["tenant_id"])


@router.post("/sources/{source_id}/sync")
async def sync(source_id: int, ky: str | None = None, s: AsyncSession = Depends(tenant_db),
               user: CurrentUser = Depends(require("nhap", "quan_tri"))) -> dict:
    if (await s.get(DataSource, source_id)) is None:
        raise HTTPException(404, "Không tìm thấy nguồn dữ liệu")
    ky = ky or date.today().strftime("%Y-%m")
    async with admin_sessionmaker()() as adm:
        run = await run_sync(adm, source_id, [s.info["tenant_id"]], ky)
    return {"so_ban_ghi": run.so_ban_ghi, "loi": run.loi}
