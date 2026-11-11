from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import tenant_fk


class StoredFile(Base):
    __tablename__ = "stored_file"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    key: Mapped[str] = mapped_column(String(80), unique=True)
    ten_goc: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(100))
    kich_thuoc: Mapped[int] = mapped_column(Integer)
    nguoi_tai_len_id: Mapped[int] = mapped_column(Integer)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
