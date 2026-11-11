from datetime import datetime

from sqlalchemy import DDL, DateTime, Integer, String, Text, event, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType


class AuditLog(Base):
    """Nhật ký truy cập & chỉnh sửa — chỉ ghi thêm (trigger chặn UPDATE/DELETE)."""

    __tablename__ = "audit_log"
    __table_args__ = {"info": {"append_only": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(500))
    query: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[int] = mapped_column(Integer)
    doi_tuong: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    before: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONType, nullable=True)


event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(
        "CREATE OR REPLACE FUNCTION audit_log_readonly() RETURNS trigger LANGUAGE plpgsql AS "
        "$$ BEGIN RAISE EXCEPTION 'audit_log chỉ cho phép ghi thêm'; END $$"
    ),
)
event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(
        "CREATE TRIGGER audit_log_no_change BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_log "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_log_readonly()"
    ),
)
