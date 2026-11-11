from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.middleware import AuditMiddleware
from app.auth.router import router as auth_router
from app.core.db import get_session
from app.indicators.router import router as indicators_router
from app.sources.router import router as sources_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="IOC-XP — Nền tảng điều hành số xã/phường",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(AuditMiddleware)

    @app.get("/api/health", tags=["he-thong"])
    async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}

    app.include_router(auth_router)
    app.include_router(sources_router)
    app.include_router(indicators_router)
    return app
