from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class Work(Base):
    """Công trình xây dựng, chỉnh trang trên địa bàn (DT II.5). Có thể gắn dự án đầu tư công hoặc không."""

    __tablename__ = "work"
    __table_args__ = (UniqueConstraint("tenant_id", "ma_cong_trinh"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma_cong_trinh: Mapped[str] = mapped_column(String(50))
    ten: Mapped[str] = mapped_column(String(400))
    loai: Mapped[str] = mapped_column(String(40))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id", ondelete="SET NULL"), nullable=True)
    dia_diem: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    toa_do_hop_le: Mapped[bool] = mapped_column(Boolean, default=True)
    don_vi_thuc_hien: Mapped[str] = mapped_column(String(300), default="")
    chu_dau_tu: Mapped[str] = mapped_column(String(300), default="")
    ngay_kc: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_ht: Mapped[date | None] = mapped_column(Date, nullable=True)
    chat_luong: Mapped[str | None] = mapped_column(String(30), nullable=True)  # dat | can_khac_phuc
    camera_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(30), default="dang_thi_cong")  # dang_thi_cong | hoan_thanh | tam_dung
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class WorkProgress(Base):
    __tablename__ = "work_progress"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("work.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = tenant_fk()
    ngay: Mapped[date] = mapped_column(Date)
    ke_hoach_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    thuc_te_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    gpmb: Mapped[str] = mapped_column(Text, default="")
    vuong_mac: Mapped[str] = mapped_column(Text, default="")
    can_quyet_dinh: Mapped[bool] = mapped_column(Boolean, default=False)
    anh_keys: Mapped[list] = mapped_column(JSONType, default=list)
    minh_chung_keys: Mapped[list] = mapped_column(JSONType, default=list)
    trang_thai_xac_nhan: Mapped[str] = mapped_column(String(20), default="tam_thoi")
    nguoi_nhap_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nguoi_xac_nhan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
