from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.principal import CurrentUser


def tenant_scope(user: CurrentUser, requested: int | None) -> int:
    """Đơn vị mà request được phép thao tác.

    Cán bộ xã/phường luôn bị khóa vào đơn vị của mình (tham số yêu cầu bị bỏ qua).
    Người dùng nhiều đơn vị phải chỉ rõ đơn vị, và đơn vị đó phải thuộc phạm vi được cấp.
    """
    if user.tenant_id is not None:
        return user.tenant_id
    if requested is None:
        raise HTTPException(400, "Cần chọn đơn vị (tham số ?tenant=)")
    if requested not in user.tenant_ids:
        raise HTTPException(404, "Không tìm thấy đơn vị")
    return requested


def scoped(stmt: Any, model: Any, tenant_id: int) -> Any:
    return stmt.where(model.tenant_id == tenant_id)


async def descendant_ids(session: AsyncSession, tenant_id: int) -> list[int]:
    rows = await session.execute(
        text(
            "WITH RECURSIVE t AS (SELECT id FROM tenant WHERE id = :id "
            "UNION ALL SELECT c.id FROM tenant c JOIN t ON c.parent_id = t.id) SELECT id FROM t"
        ),
        {"id": tenant_id},
    )
    return list(rows.scalars())
