from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import tenant_fk


class LichCongTac(Base):
    """Lịch công tác tuần của lãnh đạo (tham khảo mục "Lịch công tác" trên Cổng TTĐT)."""

    __tablename__ = "lich_cong_tac"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ngay: Mapped[date] = mapped_column(Date, index=True)
    gio_bat_dau: Mapped[str] = mapped_column(String(5))  # "08:00"
    gio_ket_thuc: Mapped[str | None] = mapped_column(String(5), nullable=True)
    noi_dung: Mapped[str] = mapped_column(Text)
    chu_tri: Mapped[str] = mapped_column(String(200), default="")
    dia_diem: Mapped[str] = mapped_column(String(300), default="")
    thanh_phan: Mapped[str] = mapped_column(Text, default="")
    don_vi_chuan_bi: Mapped[str] = mapped_column(String(300), default="")
    loai: Mapped[str] = mapped_column(String(20), default="hop")  # hop | lam_viec | tiep_dan | kiem_tra | cong_tac | khac
    trang_thai: Mapped[str] = mapped_column(String(20), default="chinh_thuc")  # chinh_thuc | du_kien | hoan
    hien_tren_tv: Mapped[bool] = mapped_column(Boolean, default=True)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    nguoi_tao_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
