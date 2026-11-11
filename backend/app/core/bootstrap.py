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


async def protect_audit_log(conn: AsyncConnection) -> None:
    """Nhật ký chỉ ghi thêm: chặn UPDATE/DELETE/TRUNCATE ở mức CSDL (kể cả với tài khoản chủ sở hữu)."""
    await conn.execute(text(
        "CREATE OR REPLACE FUNCTION audit_log_readonly() RETURNS trigger LANGUAGE plpgsql AS "
        "$$ BEGIN RAISE EXCEPTION 'audit_log chỉ cho phép ghi thêm'; END $$"
    ))
    await conn.execute(text("DROP TRIGGER IF EXISTS audit_log_no_change ON audit_log"))
    await conn.execute(text(
        "CREATE TRIGGER audit_log_no_change BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_log "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_log_readonly()"
    ))


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


def run_alembic() -> None:
    import subprocess
    from pathlib import Path

    r = subprocess.run(["alembic", "upgrade", "head"], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("Nâng cấp CSDL (alembic) thất bại:\n" + r.stderr[-3000:])


async def bootstrap() -> None:
    """Dev/test: create_all + bổ sung cột. Môi trường thật (MIGRATIONS=alembic): nâng cấp có kiểm soát bằng Alembic."""
    import_models()
    use_alembic = os.environ.get("MIGRATIONS") == "alembic"
    async with engine("admin").begin() as conn:
        await ensure_app_role(conn)
    if use_alembic:
        import asyncio

        await asyncio.to_thread(run_alembic)
    async with engine("admin").begin() as conn:
        if not use_alembic:
            await conn.run_sync(Base.metadata.create_all)
            await add_missing_columns(conn)
        await protect_audit_log(conn)
        await apply_security(conn)
