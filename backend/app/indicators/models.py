from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class IndicatorValue(Base):
    """Giá trị chỉ tiêu theo kỳ, có lý lịch số liệu (DT I.3, III.1) và phiên bản."""

    __tablename__ = "indicator_value"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicator.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = tenant_fk()
    ky_bao_cao: Mapped[str] = mapped_column(String(10), index=True)
    scope: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tdp_id: Mapped[int | None] = mapped_column(ForeignKey("residential_group.id"), nullable=True)
    gia_tri: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    du_bao: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    nguon_loai: Mapped[str] = mapped_column(String(20), default="phuong")  # phuong | chuyen_nganh | api
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_source.id"), nullable=True)
    nguon: Mapped[str] = mapped_column(String(300))
    don_vi_cung_cap: Mapped[str] = mapped_column(String(300))
    thoi_diem_chot: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    thoi_diem_dong_bo: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    trang_thai: Mapped[str] = mapped_column(String(20), default="tam_thoi")  # tam_thoi | da_xac_nhan | tu_choi
    nguoi_nhap_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nguoi_xac_nhan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nguoi_xac_nhan_ten: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ngay_xac_nhan: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    minh_chung_keys: Mapped[list] = mapped_column(JSONType, default=list)
    ly_do: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
