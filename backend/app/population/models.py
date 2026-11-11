from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import tenant_fk


class PopulationStat(Base):
    """Thống kê dân cư TỔNG HỢP (DT II.2) — không có bản ghi cá nhân.
    chi_so: nhan_khau | so_ho | sinh | tu | chuyen_den | chuyen_di."""

    __tablename__ = "population_stat"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ky: Mapped[str] = mapped_column(String(10), index=True)
    tdp_id: Mapped[int | None] = mapped_column(ForeignKey("residential_group.id", ondelete="CASCADE"), nullable=True)
    chi_so: Mapped[str] = mapped_column(String(20))
    gioi: Mapped[str] = mapped_column(String(5), default="")
    nhom_tuoi: Mapped[str] = mapped_column(String(10), default="")
    gia_tri: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
