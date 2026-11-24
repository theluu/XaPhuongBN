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
PW_CHANGE_ALLOWED = {"/api/auth/me", "/api/auth/change-password", "/api/tenant", "/api/sample-flag"}
UNAUTH = HTTPException(401, "Phiên đăng nhập không hợp lệ hoặc đã hết hạn", headers={"WWW-Authenticate": "Bearer"})


async def build_principal(user: User, requested_tenant: int | None = None) -> CurrentUser:
    """Quyền được tính RIÊNG cho đơn vị đang thao tác: chỉ gộp quyền cấp cho đơn vị đó và quyền không gắn đơn vị."""
    async with admin_sessionmaker()() as s:
        grants = list((await s.execute(select(Grant).where(Grant.user_id == user.id))).scalars())
    roles: set[str] = {g.role for g in grants}
    tenant_ids: set[int] = {g.tenant_id for g in grants if g.tenant_id is not None}
    if user.tenant_id is not None:
        tenant_ids = {user.tenant_id}
        active = user.tenant_id
    else:
        active = requested_tenant if requested_tenant in tenant_ids else None
    perms: dict[str, set[str]] = {}
    for g in grants:
        if g.tenant_id is not None and g.tenant_id != active and user.tenant_id is None:
            continue
        for n in g.nhom_du_lieu or ["*"]:
            perms.setdefault(n, set()).update(g.quyen)
    return CurrentUser(id=user.id, tenant_id=user.tenant_id, tenant_ids=sorted(tenant_ids), roles=roles,
                       permissions=perms, username=user.username)


ACT_ROLES = {"quan_tri_don_vi", "lanh_dao"}


async def act_principal(user: User, tid: int) -> CurrentUser:
    """Phiên quản trị nền tảng vào một xã/phường: đủ quyền đọc/nhập/duyệt mọi nhóm dữ liệu của riêng đơn vị đó."""
    from app.platform.models import Tenant

    async with admin_sessionmaker()() as s:
        roles = set((await s.execute(select(Grant.role).where(Grant.user_id == user.id))).scalars())
        t = await s.get(Tenant, tid)
    if "quan_tri_nen_tang" not in roles or t is None or t.cap not in ("xa", "phuong") or t.trang_thai != "hoat_dong":
        raise UNAUTH
    return CurrentUser(id=user.id, tenant_id=tid, tenant_ids=[tid], roles=set(ACT_ROLES), permissions={"*": {"doc", "nhap", "duyet"}},
                       username=user.username, dai_dien=tid)


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
    try:
        req_tenant = int(request.query_params["tenant"]) if "tenant" in request.query_params else None
    except ValueError:
        req_tenant = None
    act = payload.get("act")
    principal = await act_principal(user, int(act)) if act is not None else await build_principal(user, req_tenant)
    request.state.user = principal
    if user.phai_doi_mat_khau and request.url.path not in PW_CHANGE_ALLOWED:
        raise HTTPException(403, "Cần đổi mật khẩu tạm trước khi sử dụng hệ thống")
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
