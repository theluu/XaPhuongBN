import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.middleware import AuditMiddleware
from app.auth.router import router as auth_router
from app.core.db import get_session
from app.budget.router import router as budget_router
from app.catalog.router import router as catalog_router
from app.projects.router import router as projects_router
from app.works.router import router as works_router
from app.services_pakn.router import router as services_router
from app.population.router import router as population_router
from app.quality_of_life.router import router as qol_router
from app.alerts.router import router as alerts_router
from app.ingestion.router import router as ingestion_router
from app.compliance.router import router as compliance_router
from app.overview.router import router as overview_router
from app.reports.router import router as reports_router
from app.platform.admin import admin as unit_admin_router, platform as platform_router_admin
from app.alerts import scheduler as alert_scheduler
from app.files.router import router as files_router
from app.indicators.router import router as indicators_router
from app.indicators.workflow import router as workflow_router
from app.platform.router import router as platform_router
from app.sources.router import router as sources_router
from app.field_reports.router import router as field_reports_router
from app.operations.router import router as operations_router
from app.org.router import router as org_router
from app.dau_moi.router import router as dau_moi_router
from app.pilot.router import router as pilot_router
from app.data_admin.router import router as data_admin_router
from app.thong_bao.router import router as thong_bao_router
from app.lich.router import router as lich_router
from app.van_ban.router import router as van_ban_router
from app.tin_nhan.router import router as tin_nhan_router
from app.noti.router import router as noti_router
from app.platform.tenants_admin import router as platform_tenants_router
from app.cong_khai.router import router as cong_khai_router


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    from app.core.config import check_production, get_settings

    check_production(get_settings())
    sch = alert_scheduler.start() if os.environ.get("APP_ENV") != "test" else None
    yield
    if sch:
        sch.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title="IOC-XP — Nền tảng điều hành số xã/phường",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(AuditMiddleware)

    from fastapi.responses import JSONResponse

    from app.core.periods import KyError

    @app.exception_handler(KyError)
    async def _ky_error(_, exc: KyError) -> JSONResponse:  # noqa: ANN001
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/api/health", tags=["he-thong"])
    async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}

    app.include_router(auth_router)
    app.include_router(platform_router)
    app.include_router(platform_tenants_router)
    app.include_router(cong_khai_router)
    app.include_router(dau_moi_router)
    app.include_router(pilot_router)
    app.include_router(data_admin_router)
    app.include_router(thong_bao_router)
    app.include_router(lich_router)
    app.include_router(van_ban_router)
    app.include_router(tin_nhan_router)
    app.include_router(noti_router)
    app.include_router(sources_router)
    app.include_router(workflow_router)
    app.include_router(indicators_router)
    app.include_router(files_router)
    app.include_router(catalog_router)
    app.include_router(budget_router)
    app.include_router(projects_router)
    app.include_router(works_router)
    app.include_router(services_router)
    app.include_router(population_router)
    app.include_router(qol_router)
    app.include_router(alerts_router)
    app.include_router(ingestion_router)
    app.include_router(compliance_router)
    app.include_router(overview_router)
    app.include_router(operations_router)
    app.include_router(field_reports_router)
    app.include_router(org_router)
    app.include_router(reports_router)
    app.include_router(platform_router_admin)
    app.include_router(unit_admin_router)
    return app
