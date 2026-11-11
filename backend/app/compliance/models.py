from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import tenant_fk


class ReconciliationMemo(Base):
    """Biên bản giải trình chênh lệch (DT V.3): số hệ thống khác hồ sơ nghiệp vụ phải có giải trình trước khi chốt kỳ."""

    __tablename__ = "reconciliation_memo"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    doi_tuong: Mapped[str] = mapped_column(String(20))  # ngan_sach | giai_ngan | cong_trinh
    ref: Mapped[str] = mapped_column(String(200))
    ky: Mapped[str] = mapped_column(String(10))
    so_he_thong: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    so_ho_so: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    chenh_lech: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    giai_trinh: Mapped[str] = mapped_column(Text)
    file_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    nguoi_lap_id: Mapped[int] = mapped_column(Integer)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
