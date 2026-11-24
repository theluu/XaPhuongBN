from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class ThongBao(Base):
    """Thông báo điều hành chạy trên dải bản tin dưới đầu trang: lãnh đạo/quản trị đăng, có hiệu lực, đối tượng nhận."""

    __tablename__ = "thong_bao"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    tieu_de: Mapped[str] = mapped_column(String(300))
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    lien_ket: Mapped[str | None] = mapped_column(String(500), nullable=True)  # đường dẫn trong hệ thống hoặc bài trên Cổng TTĐT
    muc_do: Mapped[str] = mapped_column(String(20), default="thuong")  # thuong | quan_trong | khan
    tu_ngay: Mapped[date] = mapped_column(Date)
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    doi_tuong: Mapped[list] = mapped_column(JSONType, default=list)  # vai trò nhận; rỗng = mọi người
    ghim: Mapped[bool] = mapped_column(Boolean, default=False)
    hien_tren_tv: Mapped[bool] = mapped_column(Boolean, default=True)
    nguoi_tao_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
