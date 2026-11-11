"""Kết nối CSDL.

Hai vai trò Postgres:
- chủ sở hữu (ADMIN_DATABASE_URL): khởi tạo schema, seed, tác vụ hệ thống;
- ứng dụng `ioc_app` (DATABASE_URL): KHÔNG phải superuser, chịu Row-Level Security.
Mọi request nghiệp vụ dùng `tenant_session`, ngữ cảnh đơn vị được đặt lại ở đầu MỖI giao dịch.
"""
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


_engines: dict[str, AsyncEngine] = {}
_makers: dict[str, async_sessionmaker[AsyncSession]] = {}


def _get(kind: str) -> async_sessionmaker[AsyncSession]:
    if kind not in _makers:
        url = os.environ["DATABASE_URL" if kind == "app" else "ADMIN_DATABASE_URL"]
        _engines[kind] = create_async_engine(url, pool_pre_ping=True)
        _makers[kind] = async_sessionmaker(_engines[kind], expire_on_commit=False)
    return _makers[kind]


def engine(kind: str = "app") -> AsyncEngine:
    _get(kind)
    return _engines[kind]


def sessionmaker() -> async_sessionmaker[AsyncSession]:
    return _get("app")


def admin_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return _get("admin")


def reset_engine() -> None:
    _engines.clear()
    _makers.clear()


async def dispose_engine() -> None:
    for e in _engines.values():
        await e.dispose()
    reset_engine()


@event.listens_for(Session, "after_begin")
def _set_tenant_context(session: Session, transaction, connection) -> None:  # noqa: ANN001
    if not session.info.get("rls"):
        return
    ids = session.info.get("tenant_ids") or []
    value = "{" + ",".join(str(int(i)) for i in ids) + "}"
    connection.execute(text("SELECT set_config('app.tenant_ids', :v, true)"), {"v": value})


@asynccontextmanager
async def tenant_session(tenant_ids: list[int]) -> AsyncIterator[AsyncSession]:
    async with sessionmaker()() as s:
        s.info["rls"] = True
        s.info["tenant_ids"] = list(tenant_ids)
        yield s


async def get_session() -> AsyncIterator[AsyncSession]:
    """Phiên không có ngữ cảnh đơn vị: bảng có RLS trả về rỗng."""
    async with tenant_session([]) as s:
        yield s


def import_models() -> None:
    import importlib
    import pkgutil

    import app

    for mod in pkgutil.walk_packages(app.__path__, "app."):
        if mod.name.endswith(".models"):
            importlib.import_module(mod.name)
