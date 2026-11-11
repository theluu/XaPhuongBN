from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class AlertRule(Base):
    """Cấu hình quy tắc theo đơn vị (bật/tắt, tham số). Không có dòng = dùng mặc định."""

    __tablename__ = "alert_rule"
    __table_args__ = (UniqueConstraint("tenant_id", "ma"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma: Mapped[str] = mapped_column(String(40))
    bat: Mapped[bool] = mapped_column(Boolean, default=True)
    params: Mapped[dict] = mapped_column(JSONType, default=dict)


class Alert(Base):
    __tablename__ = "alert"
    __table_args__ = (UniqueConstraint("tenant_id", "dedupe_key"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    rule_ma: Mapped[str] = mapped_column(String(40), index=True)
    loai: Mapped[str] = mapped_column(String(20))  # tien_do | du_lieu | qua_han | lech_nguon | chua_gui
    nhom: Mapped[str] = mapped_column(String(30))  # nhóm dữ liệu → phân quyền xem
    muc_do: Mapped[str] = mapped_column(String(20), default="trung_binh")  # cao | trung_binh | thap
    tieu_de: Mapped[str] = mapped_column(String(500))
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    doi_tuong_ref: Mapped[str] = mapped_column(String(200))
    link: Mapped[str] = mapped_column(String(300), default="")
    ky: Mapped[str] = mapped_column(String(10), default="")
    dedupe_key: Mapped[str] = mapped_column(String(300))
    ghi_chu_chat_luong: Mapped[str | None] = mapped_column(String(300), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20), default="moi")  # moi | da_giao | dang_xu_ly | hoan_thanh | gia_han | het_hieu_luc
    phat_sinh_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lan_cuoi_kiem_tra: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)


class FollowUpCase(Base):
    """Hồ sơ theo dõi (DT IV.2): cơ quan xử lý, người phụ trách, nguyên nhân, hành động, hạn, trạng thái, kết quả."""

    __tablename__ = "follow_up_case"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    alert_id: Mapped[int] = mapped_column(ForeignKey("alert.id", ondelete="CASCADE"), unique=True)
    chi_dao: Mapped[str] = mapped_column(Text, default="")
    co_quan_xu_ly: Mapped[str] = mapped_column(String(300))
    nguoi_phu_trach: Mapped[str] = mapped_column(String(300))
    nguyen_nhan: Mapped[str] = mapped_column(Text, default="")
    hanh_dong: Mapped[str] = mapped_column(Text, default="")
    han: Mapped[date] = mapped_column(Date)
    trang_thai: Mapped[str] = mapped_column(String(20), default="da_giao")
    ket_qua: Mapped[str] = mapped_column(Text, default="")
    nguoi_giao_id: Mapped[int] = mapped_column(Integer)
    giao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cap_nhat_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    lich_su: Mapped[list] = mapped_column(JSONType, default=list)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
