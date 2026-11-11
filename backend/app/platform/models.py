from datetime import date

from sqlalchemy import JSON, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def tenant_fk(nullable: bool = False) -> Mapped:
    return mapped_column(Integer, ForeignKey("tenant.id", ondelete="CASCADE"), index=True, nullable=nullable)


class Tenant(Base):
    __tablename__ = "tenant"
    __table_args__ = {"info": {"platform": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    ma_dvhc: Mapped[str] = mapped_column(String(20), unique=True)
    ten: Mapped[str] = mapped_column(String(200))
    cap: Mapped[str] = mapped_column(String(20))  # nen_tang | tinh | xa | phuong
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("tenant.id"), nullable=True)
    logo_key: Mapped[str | None] = mapped_column(String(300), nullable=True)
    config: Mapped[dict] = mapped_column(JSONType, default=dict)
    modules: Mapped[dict] = mapped_column(JSONType, default=dict)
    trang_thai: Mapped[str] = mapped_column(String(20), default="hoat_dong")


class ResidentialGroup(Base):
    __tablename__ = "residential_group"
    __table_args__ = (UniqueConstraint("tenant_id", "ma_tdp"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma_tdp: Mapped[str] = mapped_column(String(30))
    ten: Mapped[str] = mapped_column(String(200))


class AdminUnitMapping(Base):
    """Ánh xạ các đơn vị trước sắp xếp sang đơn vị hiện hành (DT III.2)."""

    __tablename__ = "admin_unit_mapping"
    __table_args__ = (UniqueConstraint("tenant_id", "ma_cu"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma_cu: Mapped[str] = mapped_column(String(20))
    ten_cu: Mapped[str] = mapped_column(String(200))
    hieu_luc_den: Mapped[date | None] = mapped_column(Date, nullable=True)


class SharedCatalog(Base):
    """Danh mục dùng chung do nền tảng quản lý."""

    __tablename__ = "shared_catalog"
    __table_args__ = (UniqueConstraint("loai", "ma"), {"info": {"platform": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    loai: Mapped[str] = mapped_column(String(50), index=True)
    ma: Mapped[str] = mapped_column(String(50))
    ten: Mapped[str] = mapped_column(String(300))
    thuoc_tinh: Mapped[dict] = mapped_column(JSONType, default=dict)
