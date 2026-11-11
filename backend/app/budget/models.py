from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import tenant_fk


class BudgetLine(Base):
    """Số liệu thu/chi lũy kế đến hết kỳ. scope: dia_ban (thu phát sinh trên địa bàn) | ns_phuong (ngân sách phường)."""

    __tablename__ = "budget_line"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    nam: Mapped[int] = mapped_column(Integer, index=True)
    ky: Mapped[str] = mapped_column(String(10), index=True)  # "2026-10": lũy kế đến hết tháng
    loai: Mapped[str] = mapped_column(String(5))  # thu | chi
    nhom_ma: Mapped[str] = mapped_column(String(40))
    nhiem_vu: Mapped[str | None] = mapped_column(String(40), nullable=True)
    scope: Mapped[str] = mapped_column(String(20))
    du_toan: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    ke_hoach_ky: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    thuc_hien: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    uoc_th: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    nguon_loai: Mapped[str] = mapped_column(String(20), default="bao_cao_chot")  # api | bao_cao_chot
    trang_thai_doi_soat: Mapped[str] = mapped_column(String(20), default="cho_doi_soat")
    ngay_chot: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
