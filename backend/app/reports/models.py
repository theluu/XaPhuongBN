from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class MeetingSession(Base):
    """Phiên khai thác phục vụ giao ban (DT V.3: ≥ 02 phiên có biên bản)."""

    __tablename__ = "meeting_session"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ngay: Mapped[date] = mapped_column(Date)
    ky: Mapped[str] = mapped_column(String(10))
    thanh_phan: Mapped[str] = mapped_column(Text, default="")
    ket_luan: Mapped[str] = mapped_column(Text, default="")
    so_canh_bao: Mapped[int] = mapped_column(Integer, default=0)
    so_giao: Mapped[int] = mapped_column(Integer, default=0)
    so_hoan_thanh: Mapped[int] = mapped_column(Integer, default=0)
    noi_dung: Mapped[dict] = mapped_column(JSONType, default=dict)
    file_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    nguoi_lap_id: Mapped[int] = mapped_column(Integer)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
