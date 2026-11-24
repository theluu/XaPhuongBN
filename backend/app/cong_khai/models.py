from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class CongBo(Base):
    """Bản công bố kỳ ra trang công khai: ảnh chụp cố định các chỉ tiêu phường đã duyệt công khai, chỉ gồm số đã xác nhận.

    Trang công khai chỉ đọc bản công bố mới nhất — số liệu nội bộ thay đổi sau đó không lộ ra ngoài cho tới khi lãnh đạo công bố lại.
    """

    __tablename__ = "cong_bo"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ky: Mapped[str] = mapped_column(String(10), index=True)
    du_lieu: Mapped[dict] = mapped_column(JSONType, default=dict)
    nguoi_cong_bo_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nguoi_cong_bo_ten: Mapped[str] = mapped_column(String(200), default="")
    cong_bo_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    thu_hoi_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
