from collections.abc import AsyncIterator, Callable

from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Grant, User
from app.auth.security import decode_token
from app.core.db import admin_sessionmaker, tenant_session
from app.core.principal import CurrentUser
from app.core.tenancy import tenant_scope

_bearer = HTTPBearer(auto_error=False)
UNAUTH = HTTPException(401, "Phiên đăng nhập không hợp lệ hoặc đã hết hạn", headers={"WWW-Authenticate": "Bearer"})


async def build_principal(user: User) -> CurrentUser:
    async with admin_sessionmaker()() as s:
        grants = list((await s.execute(select(Grant).where(Grant.user_id == user.id))).scalars())
    perms: dict[str, set[str]] = {}
    roles: set[str] = set()
    tenant_ids: set[int] = set()
    for g in grants:
        roles.add(g.role)
        if g.tenant_id is not None:
            tenant_ids.add(g.tenant_id)
        for n in g.nhom_du_lieu or ["*"]:
            perms.setdefault(n, set()).update(g.quyen)
    if user.tenant_id is not None:
        tenant_ids = {user.tenant_id}
    return CurrentUser(id=user.id, tenant_id=user.tenant_id, tenant_ids=sorted(tenant_ids), roles=roles,
                       permissions=perms, username=user.username)


async def get_current_user(
    request: Request, cred: HTTPAuthorizationCredentials | None = Depends(_bearer)
) -> CurrentUser:
    if cred is None:
        raise UNAUTH
    try:
        payload = decode_token(cred.credentials)
    except Exception as e:  # noqa: BLE001
        raise UNAUTH from e
    async with admin_sessionmaker()() as s:
        user = await s.get(User, int(payload["sub"]))
    if user is None or user.trang_thai != "hoat_dong" or user.token_version != payload.get("tv"):
        raise UNAUTH
    principal = await build_principal(user)
    request.state.user = principal
    return principal


def require(quyen: str, nhom: str | None = None) -> Callable:
    async def dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.can(quyen, nhom):
            raise HTTPException(403, "Bạn không có quyền thực hiện thao tác này")
        return user

    return dep


async def tenant_db(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    tenant: int | None = Query(None, description="Đơn vị (chỉ cho tài khoản nhiều đơn vị)"),
) -> AsyncIterator[AsyncSession]:
    tid = tenant_scope(user, tenant)
    request.state.tenant_id = tid
    async with tenant_session([tid]) as s:
        s.info["tenant_id"] = tid
        yield s
