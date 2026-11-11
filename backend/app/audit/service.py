from typing import Any

from app.audit.models import AuditLog
from app.core.db import admin_sessionmaker


async def record(
    *, method: str, path: str, status: int, user_id: int | None = None, tenant_id: int | None = None,
    ip: str | None = None, query: str = "", doi_tuong: str | None = None,
    before: dict[str, Any] | None = None, after: dict[str, Any] | None = None,
) -> None:
    async with admin_sessionmaker()() as s:
        s.add(AuditLog(method=method, path=path, status=status, user_id=user_id, tenant_id=tenant_id, ip=ip,
                       query=query, doi_tuong=doi_tuong, before=before, after=after))
        await s.commit()


async def record_change(user, tenant_id: int | None, doi_tuong: str, before: dict | None, after: dict | None) -> None:  # noqa: ANN001
    await record(method="CHANGE", path=doi_tuong, status=200, user_id=user.id, tenant_id=tenant_id,
                 doi_tuong=doi_tuong, before=before, after=after)
