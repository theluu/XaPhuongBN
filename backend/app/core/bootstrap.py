"""Khởi tạo CSDL: vai trò ứng dụng, extension, bảng, RLS, phân quyền mức CSDL."""
import os
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.db import Base, engine, import_models

APP_ROLE = "ioc_app"


def _app_password() -> str:
    m = re.match(r"^[^:]+://[^:]+:([^@]+)@", os.environ["DATABASE_URL"])
    if not m:
        raise RuntimeError("DATABASE_URL phải chứa mật khẩu của vai trò ioc_app")
    return m.group(1)


async def ensure_app_role(conn: AsyncConnection) -> None:
    exists = (await conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname=:r"), {"r": APP_ROLE})).scalar()
    pw = _app_password().replace("'", "''")
    if not exists:
        await conn.execute(text(f"CREATE ROLE {APP_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{pw}'"))
    else:
        await conn.execute(text(f"ALTER ROLE {APP_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{pw}'"))


async def apply_security(conn: AsyncConnection) -> None:
    await conn.execute(text(
        "CREATE OR REPLACE FUNCTION app_tenant_ids() RETURNS int[] LANGUAGE sql STABLE AS "
        "$$ SELECT COALESCE(NULLIF(current_setting('app.tenant_ids', true), ''), '{}')::int[] $$"
    ))
    await conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}"))
    await conn.execute(text(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}"))
    for table in Base.metadata.sorted_tables:
        info = table.info
        name = table.name
        await conn.execute(text(f'REVOKE ALL ON "{name}" FROM {APP_ROLE}'))
        if info.get("platform"):
            grants = "SELECT"
        elif info.get("append_only"):
            grants = "SELECT, INSERT"
        else:
            grants = "SELECT, INSERT, UPDATE, DELETE"
        await conn.execute(text(f'GRANT {grants} ON "{name}" TO {APP_ROLE}'))
        if info.get("rls"):
            await conn.execute(text(f'ALTER TABLE "{name}" ENABLE ROW LEVEL SECURITY'))
            await conn.execute(text(f'DROP POLICY IF EXISTS tenant_isolation ON "{name}"'))
            await conn.execute(text(
                f'CREATE POLICY tenant_isolation ON "{name}" '
                "USING (tenant_id IS NULL OR tenant_id = ANY(app_tenant_ids())) "
                "WITH CHECK (tenant_id = ANY(app_tenant_ids()))"
            ))


async def add_missing_columns(conn: AsyncConnection) -> list[str]:
    """Bổ sung cột mới (nullable/có default) cho CSDL đã tồn tại — dùng cho môi trường dev trước khi có Alembic baseline."""
    added = []
    for table in Base.metadata.sorted_tables:
        have = set((await conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:t"), {"t": table.name})).scalars())
        if not have:
            continue
        for col in table.columns:
            if col.name not in have:
                ddl = col.type.compile(dialect=conn.dialect)
                await conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl}'))
                added.append(f"{table.name}.{col.name}")
    return added


async def bootstrap() -> None:
    import_models()
    async with engine("admin").begin() as conn:
        await ensure_app_role(conn)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)
        await add_missing_columns(conn)
        await apply_security(conn)
