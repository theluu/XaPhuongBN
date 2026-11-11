import pytest
from sqlalchemy import select, text

from app.audit.models import AuditLog
from app.core.db import admin_sessionmaker
from tests.factories import bearer, login, make_tenant, make_user


async def _rows(user_id: int) -> list[AuditLog]:
    async with admin_sessionmaker()() as s:
        return list((await s.execute(select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.id))).scalars())


async def test_every_request_audited(client):
    t = await make_tenant()
    u = await make_user(t)
    tok = await login(client, u["username"])
    await client.get("/api/auth/me?x=1", headers=bearer(tok))
    rows = await _rows(u["id"])
    paths = [(r.method, r.path) for r in rows]
    assert ("POST", "/api/auth/login") in paths
    assert ("GET", "/api/auth/me") in paths
    me = next(r for r in rows if r.path == "/api/auth/me")
    assert me.status == 200 and me.tenant_id == t and me.query == "x=1"


async def test_failed_login_audited(client):
    await client.post("/api/auth/login", json={"username": "khong_co_ai", "password": "x"})
    async with admin_sessionmaker()() as s:
        r = (await s.execute(select(AuditLog).where(AuditLog.doi_tuong == "dang_nhap:khong_co_ai"))).scalars().first()
    assert r is not None and r.status == 401


async def test_audit_append_only(client):
    t = await make_tenant()
    u = await make_user(t)
    await login(client, u["username"])
    async with admin_sessionmaker()() as s:
        with pytest.raises(Exception):
            await s.execute(text("UPDATE audit_log SET path='x'"))
            await s.commit()
    async with admin_sessionmaker()() as s:
        with pytest.raises(Exception):
            await s.execute(text("DELETE FROM audit_log"))
            await s.commit()


async def test_unauthenticated_access_audited(client):
    await client.get("/api/auth/me?probe=invalid-token", headers={"Authorization": "Bearer khong-hop-le"})
    async with admin_sessionmaker()() as s:
        r = (await s.execute(select(AuditLog).where(AuditLog.query == "probe=invalid-token"))).scalars().first()
    assert r is not None and r.status == 401 and r.user_id is None
