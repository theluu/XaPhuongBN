from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class PackTracked:
    nguon_pack: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pack_phien_ban: Mapped[int | None] = mapped_column(Integer, nullable=True)
    da_chinh_sua: Mapped[bool] = mapped_column(Boolean, default=False)


class Indicator(PackTracked, Base):
    __tablename__ = "indicator"
    __table_args__ = (UniqueConstraint("tenant_id", "ma_chi_tieu"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int | None] = tenant_fk(nullable=True)
    ma_chi_tieu: Mapped[str] = mapped_column(String(40))
    ten: Mapped[str] = mapped_column(String(400))
    dinh_nghia: Mapped[str] = mapped_column(Text)
    cong_thuc: Mapped[str] = mapped_column(Text)
    pham_vi_dia_ban: Mapped[str] = mapped_column(String(300))
    nhom: Mapped[str] = mapped_column(String(40), index=True)  # nhóm dữ liệu dùng cho phân quyền
    phan_he: Mapped[str] = mapped_column(String(40), index=True)
    bo: Mapped[list] = mapped_column(JSONType, default=list)  # VD ["NQ01"]
    don_vi_do: Mapped[str] = mapped_column(String(60))
    chieu: Mapped[str] = mapped_column(String(20))
    nguong_toan_tu: Mapped[str | None] = mapped_column(String(2), nullable=True)
    muc_tieu: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    muc_tieu_khoang: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    muc_tieu_2030: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    han_muc_tieu_nam: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scope: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nguon_mac_dinh: Mapped[str] = mapped_column(String(300))
    nguon_uu_tien: Mapped[list] = mapped_column(JSONType, default=lambda: ["phuong", "chuyen_nganh", "api"])
    don_vi_chu_quan: Mapped[str] = mapped_column(String(300))
    nguoi_xac_nhan_mac_dinh: Mapped[str] = mapped_column(String(200), default="")
    ky_cap_nhat: Mapped[str] = mapped_column(String(20))
    han_cap_nhat_ngay: Mapped[int] = mapped_column(Integer, default=10)
    dinh_dang: Mapped[str] = mapped_column(String(20), default="so")
    phan_loai_thong_tin: Mapped[str] = mapped_column(String(20), default="noi_bo")
    can_minh_chung: Mapped[bool] = mapped_column(Boolean, default=False)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")


class IndicatorPlan(Base):
    """Kế hoạch từng kỳ — mốc so sánh tiến độ (DT II.1, IV.2). Không nội suy."""

    __tablename__ = "indicator_plan"
    __table_args__ = (UniqueConstraint("indicator_id", "tenant_id", "nam", "ky"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicator.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int] = tenant_fk()
    nam: Mapped[int] = mapped_column(Integer)
    ky: Mapped[str] = mapped_column(String(10))  # "2026" | "2026-Q3" | "2026-10" | "2026-W40"
    gia_tri_ke_hoach: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    can_cu: Mapped[str] = mapped_column(String(300), default="")


class Program(PackTracked, Base):
    """Nhiệm vụ, chương trình trọng tâm (NQ 01: 08 nhiệm vụ)."""

    __tablename__ = "program"
    __table_args__ = (UniqueConstraint("tenant_id", "ma"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma: Mapped[str] = mapped_column(String(40))
    ten: Mapped[str] = mapped_column(String(400))
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    don_vi_chu_tri: Mapped[str] = mapped_column(String(300), default="")
    indicator_ids: Mapped[list] = mapped_column(JSONType, default=list)
    trang_thai: Mapped[str] = mapped_column(String(30), default="dang_thuc_hien")


class Scenario(PackTracked, Base):
    """Kịch bản điều hành = bộ chỉ tiêu + quy tắc cảnh báo + bố cục (15 + 02 kịch bản)."""

    __tablename__ = "scenario"
    __table_args__ = (UniqueConstraint("tenant_id", "ma"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma: Mapped[str] = mapped_column(String(40))
    ten: Mapped[str] = mapped_column(String(400))
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    la_bo_sung: Mapped[bool] = mapped_column(Boolean, default=False)
    indicator_ids: Mapped[list] = mapped_column(JSONType, default=list)
    rule_codes: Mapped[list] = mapped_column(JSONType, default=list)
    layout: Mapped[dict] = mapped_column(JSONType, default=dict)
    trang_thai: Mapped[str] = mapped_column(String(30), default="hoat_dong")


class TemplatePack(Base):
    __tablename__ = "template_pack"
    __table_args__ = {"info": {"platform": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(80), unique=True)
    ten: Mapped[str] = mapped_column(String(300))
    phien_ban: Mapped[int] = mapped_column(Integer)
    noi_dung: Mapped[dict] = mapped_column(JSONType)
