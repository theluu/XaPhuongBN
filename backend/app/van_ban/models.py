from datetime import date

from sqlalchemy import Boolean, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class VanBan(Base):
    """Văn bản chỉ đạo điều hành (nghị quyết, quyết định, chỉ thị, kế hoạch, thông báo kết luận, công văn) gắn với nhiệm vụ chỉ đạo."""

    __tablename__ = "van_ban"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    so_ky_hieu: Mapped[str] = mapped_column(String(100))
    ngay_ban_hanh: Mapped[date] = mapped_column(Date, index=True)
    loai: Mapped[str] = mapped_column(String(20))
    co_quan_ban_hanh: Mapped[str] = mapped_column(String(300))
    nguoi_ky: Mapped[str] = mapped_column(String(200), default="")
    trich_yeu: Mapped[str] = mapped_column(Text)
    file_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lien_ket: Mapped[str | None] = mapped_column(String(500), nullable=True)
    han_thuc_hien: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(20), default="con_hieu_luc")  # con_hieu_luc | het_hieu_luc
    nhiem_vu_ids: Mapped[list] = mapped_column(JSONType, default=list)  # follow_up_case.id
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
