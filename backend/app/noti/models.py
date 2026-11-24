from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import tenant_fk


class Noti(Base):
    """Thông báo cá nhân (chuông): được giao việc, có kết quả, số liệu chờ xác nhận/bị từ chối, tin nhắn, công văn, cảnh báo mới."""

    __tablename__ = "noti"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    loai: Mapped[str] = mapped_column(String(30))  # giao_viec | ket_qua | cho_xac_nhan | tu_choi | tin_nhan | cong_van | canh_bao | thong_bao
    tieu_de: Mapped[str] = mapped_column(String(300))
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    lien_ket: Mapped[str | None] = mapped_column(String(300), nullable=True)
    muc_do: Mapped[str] = mapped_column(String(20), default="thuong")  # thuong | quan_trong | khan
    khoa: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)  # gộp thông báo cùng việc (VD tin:12)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    da_doc_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
