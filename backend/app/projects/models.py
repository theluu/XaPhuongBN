from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk

LOP = {1: "Phường làm chủ đầu tư", 2: "Cơ quan cấp thành phố làm chủ đầu tư, thi công trên địa bàn", 3: "Dự án khác, chỉ theo dõi thông tin"}


class Project(Base):
    """Dự án đầu tư công — 3 lớp (DT II.4). Chỉ lớp 1 tính vào tỷ lệ giải ngân ngân sách phường."""

    __tablename__ = "project"
    __table_args__ = (UniqueConstraint("tenant_id", "ma_du_an"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma_du_an: Mapped[str] = mapped_column(String(50))
    ten: Mapped[str] = mapped_column(String(400))
    lop: Mapped[int] = mapped_column(Integer)
    chu_dau_tu: Mapped[str] = mapped_column(String(300))
    nguon_von: Mapped[str] = mapped_column(String(40))
    tong_muc_dt: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    dia_diem: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    ngay_ht_ke_hoach: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(30), default="dang_thuc_hien")
    don_vi_phu_trach: Mapped[str] = mapped_column(String(300), default="")
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class _Child:
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = tenant_fk()
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)


class CapitalPlan(_Child, Base):
    """Kế hoạch vốn: ky='2026' = kế hoạch vốn năm; ky='2026-10' = lịch vốn lũy kế đã duyệt đến hết tháng."""

    __tablename__ = "project_capital_plan"
    __table_args__ = (UniqueConstraint("project_id", "ky"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    nam: Mapped[int] = mapped_column(Integer)
    ky: Mapped[str] = mapped_column(String(10))
    ke_hoach_von: Mapped[Decimal] = mapped_column(Numeric(20, 2))


class Disbursement(_Child, Base):
    __tablename__ = "project_disbursement"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(10))
    luy_ke: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    khoi_luong_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    trang_thai_xac_nhan: Mapped[str] = mapped_column(String(20), default="tam_thoi")
    nguon: Mapped[str] = mapped_column(String(200), default="Chủ đầu tư báo cáo")


class Milestone(_Child, Base):
    __tablename__ = "project_milestone"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    loai: Mapped[str] = mapped_column(String(20))  # dau_thau | khoi_cong | thi_cong | nghiem_thu | ban_giao
    han: Mapped[date] = mapped_column(Date)
    ngay_thuc_te: Mapped[date | None] = mapped_column(Date, nullable=True)


class ProjectIssue(_Child, Base):
    __tablename__ = "project_issue"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    noi_dung: Mapped[str] = mapped_column(Text)
    nguyen_nhan: Mapped[str] = mapped_column(Text, default="")
    trach_nhiem: Mapped[str] = mapped_column(String(300), default="")
    huong_xu_ly: Mapped[str] = mapped_column(Text, default="")
    can_quyet_dinh: Mapped[bool] = mapped_column(Boolean, default=False)
    ho_so_keys: Mapped[list] = mapped_column(JSONType, default=list)
    han: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20), default="dang_xu_ly")
