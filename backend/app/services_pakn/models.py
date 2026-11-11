from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import tenant_fk


class AdminServiceStat(Base):
    """Số liệu hồ sơ TTHC tổng hợp theo ngày, bộ phận (DT II.6). Không lưu hồ sơ cá nhân."""

    __tablename__ = "admin_service_stat"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ngay: Mapped[date] = mapped_column(Date, index=True)
    bo_phan: Mapped[str] = mapped_column(String(200))
    linh_vuc: Mapped[str] = mapped_column(String(40), default="")
    tiep_nhan: Mapped[int] = mapped_column(Integer, default=0)
    giai_quyet: Mapped[int] = mapped_column(Integer, default=0)
    dung_han: Mapped[int] = mapped_column(Integer, default=0)
    qua_han: Mapped[int] = mapped_column(Integer, default=0)
    truc_tuyen: Mapped[int] = mapped_column(Integer, default=0)
    nguon: Mapped[str] = mapped_column(String(20), default="bieu_mau")  # api | bieu_mau
    trang_thai: Mapped[str] = mapped_column(String(20), default="tam_thoi")
    nguoi_nhap_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class FeedbackTicket(Base):
    """Phản ánh kiến nghị — chỉ thông tin xử lý, KHÔNG có thông tin định danh người phản ánh."""

    __tablename__ = "feedback_ticket"
    __table_args__ = (UniqueConstraint("tenant_id", "ma"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma: Mapped[str] = mapped_column(String(80))
    loai_viec: Mapped[str] = mapped_column(String(40))
    linh_vuc: Mapped[str] = mapped_column(String(40), default="")
    tdp_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ngay_nhan: Mapped[date] = mapped_column(Date, index=True)
    han_xu_ly: Mapped[date] = mapped_column(Date)
    so_ngay_quy_dinh: Mapped[int] = mapped_column(Integer)
    ngay_hoan_thanh: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20))  # tiep_nhan | dang_xu_ly | qua_han | hoan_thanh
    trang_thai_tra_loi: Mapped[str] = mapped_column(String(20), default="chua_tra_loi")
    danh_gia_hai_long: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
