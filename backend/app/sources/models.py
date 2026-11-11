from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class DataSource(Base):
    """Nguồn dữ liệu — đối tượng của nền tảng; tenant_id NULL = nguồn dùng chung."""

    __tablename__ = "data_source"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int | None] = tenant_fk(nullable=True)
    ma: Mapped[str] = mapped_column(String(80), unique=True)
    ten: Mapped[str] = mapped_column(String(300))
    loai: Mapped[str] = mapped_column(String(20))  # api | excel | csv | bieu_mau
    co_quan_cung_cap: Mapped[str] = mapped_column(String(300))
    nhom_du_lieu: Mapped[str] = mapped_column(String(40), index=True)
    config: Mapped[dict] = mapped_column(JSONType, default=dict)
    endpoints: Mapped[list] = mapped_column(JSONType, default=list)  # [{ma, ten, ket_noi, tra_du_lieu}]
    trang_thai: Mapped[str] = mapped_column(String(30), default="dang_ket_noi")
    # dang_ket_noi | hoat_dong | hoat_dong_mot_phan | khong_tra_du_lieu | loi
    phap_ly_chia_se: Mapped[str] = mapped_column(String(30), default="chua_cho_phep")
    lan_dong_bo_cuoi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SyncRun(Base):
    __tablename__ = "sync_run"
    __table_args__ = {"info": {"platform": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_source.id", ondelete="CASCADE"), index=True)
    tenant_ids: Mapped[list] = mapped_column(JSONType, default=list)
    ky: Mapped[str] = mapped_column(String(10))
    bat_dau: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ket_thuc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    so_ban_ghi: Mapped[int] = mapped_column(Integer, default=0)
    loi: Mapped[str] = mapped_column(Text, default="")
