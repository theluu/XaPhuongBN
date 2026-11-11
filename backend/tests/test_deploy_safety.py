import os
import subprocess

import pytest
from sqlalchemy import inspect, text

from app.core.config import Settings, check_production
from app.core.db import Base, import_models


def test_production_refuses_default_secrets():
    s = Settings(DATABASE_URL="x", APP_ENV="production", JWT_SECRET="dev-only-secret-change-me-dev-only-secret-change-me", REQUIRE_2FA=True)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        check_production(s)
    s = Settings(DATABASE_URL="x", APP_ENV="production", JWT_SECRET="a" * 64, REQUIRE_2FA=False)
    with pytest.raises(RuntimeError, match="REQUIRE_2FA"):
        check_production(s)
    check_production(Settings(DATABASE_URL="x", APP_ENV="production", JWT_SECRET="b" * 64, REQUIRE_2FA=True))
    check_production(Settings(DATABASE_URL="x", APP_ENV="local"))


async def test_alembic_baseline_matches_models():
    from sqlalchemy.ext.asyncio import create_async_engine

    base = os.environ["ADMIN_DATABASE_URL"].rsplit("/", 1)[0]
    eng = create_async_engine(base + "/postgres", isolation_level="AUTOCOMMIT")
    async with eng.connect() as c:
        await c.execute(text('DROP DATABASE IF EXISTS "ioc_migrate" WITH (FORCE)'))
        await c.execute(text('CREATE DATABASE "ioc_migrate"'))
    await eng.dispose()
    env = {**os.environ, "ADMIN_DATABASE_URL": base + "/ioc_migrate"}
    r = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True, env=env, cwd=os.path.dirname(os.path.dirname(__file__)))
    assert r.returncode == 0, r.stderr[-2000:]
    import_models()
    target = create_async_engine(base + "/ioc_migrate")
    async with target.connect() as c:
        tables = await c.run_sync(lambda sc: {t: {col["name"] for col in inspect(sc).get_columns(t)} for t in inspect(sc).get_table_names()})
    await target.dispose()
    tables.pop("alembic_version", None)
    assert set(tables) == {t.name for t in Base.metadata.sorted_tables}
    for t in Base.metadata.sorted_tables:
        assert tables[t.name] == set(t.c.keys()), t.name
