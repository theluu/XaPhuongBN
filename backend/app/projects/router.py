from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.projects.models import Project
from app.projects.service import detail, list_projects, summary

router = APIRouter(prefix="/api/projects", tags=["dau-tu-cong"])
DOC = require("doc", "dau_tu_cong")


def _ky() -> str:
    return date.today().strftime("%Y-%m")


@router.get("")
async def projects(lop: int | None = None, ky: str = Query(default_factory=_ky), s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> list:
    return jsonable(await list_projects(s, s.info["tenant_id"], ky, lop))


@router.get("/summary")
async def projects_summary(ky: str = Query(default_factory=_ky), s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> dict:
    return jsonable(await summary(s, s.info["tenant_id"], ky))


@router.get("/geojson")
async def geojson(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> dict:
    rows = (await s.execute(select(Project).where(Project.tenant_id == s.info["tenant_id"], Project.lat.is_not(None), Project.lng.is_not(None)))).scalars()
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(p.lng), float(p.lat)]},
         "properties": {"ma": p.ma_du_an, "ten": p.ten, "lop": p.lop, "loai": "du_an"}} for p in rows]}


@router.get("/{ma}")
async def project_detail(ma: str, ky: str = Query(default_factory=_ky), s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> dict:
    p = (await s.execute(select(Project).where(Project.tenant_id == s.info["tenant_id"], Project.ma_du_an == ma))).scalar()
    if p is None:
        raise HTTPException(404, "Không tìm thấy dự án")
    return jsonable(await detail(s, p, ky))
