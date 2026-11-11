from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.audit.service import record


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


SKIP = {"/api/health", "/api/auth/login"}  # đăng nhập được ghi riêng kèm kết quả


class AuditMiddleware(BaseHTTPMiddleware):
    """Ghi nhật ký MỌI request đã xác thực (DT V.3: 100% truy cập và chỉnh sửa có nhật ký)."""

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        response = await call_next(request)
        user = getattr(request.state, "user", None)
        path = request.url.path
        if user is not None or (path.startswith("/api/") and path not in SKIP):
            await record(
                method=request.method, path=request.url.path, query=request.url.query, status=response.status_code,
                user_id=user.id if user else None,
                tenant_id=getattr(request.state, "tenant_id", None) or (user.tenant_id if user else None),
                ip=client_ip(request),
            )
        return response
