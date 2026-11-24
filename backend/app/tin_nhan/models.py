from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class HoiThoai(Base):
    """Cuộc trao đổi nội bộ: trực tiếp hai người, nhóm, hoặc gắn với một việc (cảnh báo, phản ánh, nhiệm vụ)."""

    __tablename__ = "hoi_thoai"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    tieu_de: Mapped[str] = mapped_column(String(300), default="")
    loai: Mapped[str] = mapped_column(String(20), default="nhom")  # truc_tiep | nhom | viec
    lien_ket_loai: Mapped[str | None] = mapped_column(String(20), nullable=True)  # canh_bao | phan_anh
    lien_ket_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    lien_ket_ten: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lien_ket_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    tao_boi: Mapped[int] = mapped_column(Integer)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cap_nhat_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class ThanhVien(Base):
    __tablename__ = "hoi_thoai_thanh_vien"
    __table_args__ = (UniqueConstraint("hoi_thoai_id", "user_id"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    hoi_thoai_id: Mapped[int] = mapped_column(ForeignKey("hoi_thoai.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    doc_den: Mapped[int] = mapped_column(Integer, default=0)  # id tin nhắn cuối đã đọc
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class TinNhan(Base):
    __tablename__ = "tin_nhan"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    hoi_thoai_id: Mapped[int] = mapped_column(ForeignKey("hoi_thoai.id", ondelete="CASCADE"), index=True)
    nguoi_gui_id: Mapped[int] = mapped_column(Integer)
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    van_ban_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # công văn xử lý gửi kèm (van_ban.id)
    he_thong: Mapped[bool] = mapped_column(Boolean, default=False)  # dòng thông báo của hệ thống (thêm người…)
    gui_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class TepTinNhan(Base):
    """Tệp đính kèm tin nhắn — chỉ thành viên hội thoại tải được."""

    __tablename__ = "tin_nhan_tep"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    tin_nhan_id: Mapped[int] = mapped_column(ForeignKey("tin_nhan.id", ondelete="CASCADE"), index=True)
    hoi_thoai_id: Mapped[int] = mapped_column(Integer, index=True)
    key: Mapped[str] = mapped_column(String(80), index=True)
    ten: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(100))
    kich_thuoc: Mapped[int] = mapped_column(Integer)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
