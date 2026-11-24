from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import tenant_fk


class TinNgoai(Base):
    """Tin lấy từ nguồn RSS/Atom do đơn vị cấu hình (VD Cổng TTĐT phường/thành phố) để chạy trên dải bản tin."""

    __tablename__ = "tin_ngoai"
    __table_args__ = (UniqueConstraint("tenant_id", "guid"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    nguon: Mapped[str] = mapped_column(String(500))
    ten_nguon: Mapped[str] = mapped_column(String(200))
    guid: Mapped[str] = mapped_column(String(500))
    tieu_de: Mapped[str] = mapped_column(String(500))
    lien_ket: Mapped[str] = mapped_column(String(500))
    ngay_dang: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lay_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
