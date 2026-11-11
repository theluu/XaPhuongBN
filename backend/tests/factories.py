import uuid

from app.auth.models import Grant, User
from app.auth.security import hash_password
from app.auth.roles import default_grants
from app.core.db import admin_sessionmaker
from app.platform.models import Tenant

PASSWORD = "Mat-khau-Test@2026"


def uid(prefix: str = "u") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def make_tenant(ten: str = "Phường Thử", cap: str = "phuong", parent_id: int | None = None) -> int:
    async with admin_sessionmaker()() as s:
        t = Tenant(ma_dvhc=uid("DV"), ten=ten, cap=cap, parent_id=parent_id, config={}, modules={})
        s.add(t)
        await s.commit()
        return t.id


async def make_user(
    tenant_id: int | None,
    role: str = "lanh_dao",
    nhom: list[str] | None = None,
    totp_secret: str | None = None,
    extra_grants: list[tuple[int, str, list[str] | None, list[str]]] | None = None,
) -> dict:
    username = uid(role)
    async with admin_sessionmaker()() as s:
        u = User(
            tenant_id=tenant_id, username=username, ho_ten="Người Thử", don_vi="UBND", chuc_danh="Cán bộ",
            password_hash=hash_password(PASSWORD), totp_secret=totp_secret, trang_thai="hoat_dong",
        )
        s.add(u)
        await s.flush()
        for g_nhom, g_quyen in default_grants(role, nhom):
            s.add(Grant(user_id=u.id, tenant_id=tenant_id, role=role, nhom_du_lieu=g_nhom, quyen=g_quyen))
        for t_id, r, g_nhom, g_quyen in extra_grants or []:
            s.add(Grant(user_id=u.id, tenant_id=t_id, role=r, nhom_du_lieu=g_nhom, quyen=g_quyen))
        await s.commit()
        return {"id": u.id, "username": username, "tenant_id": tenant_id}


async def login(client, username: str, otp: str | None = None) -> str:
    body = {"username": username, "password": PASSWORD}
    if otp:
        body["otp"] = otp
    r = await client.post("/api/auth/login", json=body)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
