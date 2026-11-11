import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DB = "ioc_test"
os.environ["APP_ENV"] = "test"


def _with_db(url: str, db: str) -> str:
    return url.rsplit("/", 1)[0] + f"/{db}"


@pytest_asyncio.fixture(scope="session", autouse=True, loop_scope="session")
async def _test_database():
    admin = create_async_engine(_with_db(os.environ["ADMIN_DATABASE_URL"], "postgres"), isolation_level="AUTOCOMMIT")
    async with admin.connect() as c:
        await c.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)'))
        await c.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    await admin.dispose()
    os.environ["ADMIN_DATABASE_URL"] = _with_db(os.environ["ADMIN_DATABASE_URL"], TEST_DB)
    os.environ["DATABASE_URL"] = _with_db(os.environ["DATABASE_URL"], TEST_DB)
    from app.core import db
    from app.core.bootstrap import bootstrap

    db.reset_engine()
    await bootstrap()
    yield
    await db.dispose_engine()


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    from app.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
