from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class User(Base):
    __tablename__ = "app_user"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int | None] = tenant_fk(nullable=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    ho_ten: Mapped[str] = mapped_column(String(200))
    don_vi: Mapped[str] = mapped_column(String(200), default="")
    chuc_danh: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pham_vi_khai_thac: Mapped[str] = mapped_column(String(500), default="")
    password_hash: Mapped[str | None] = mapped_column(String(300), nullable=True)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_last: Mapped[int | None] = mapped_column(Integer, nullable=True)  # bước thời gian của mã OTP đã dùng gần nhất
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    trang_thai: Mapped[str] = mapped_column(String(20), default="cho_duyet")  # cho_duyet | hoat_dong | thu_hoi
    phai_doi_mat_khau: Mapped[bool] = mapped_column(Boolean, default=False)
    nguoi_phe_duyet_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    ly_do_thu_hoi: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Grant(Base):
    __tablename__ = "user_grant"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[int | None] = tenant_fk(nullable=True)
    role: Mapped[str] = mapped_column(String(40))
    nhom_du_lieu: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    quyen: Mapped[list] = mapped_column(JSONType)
