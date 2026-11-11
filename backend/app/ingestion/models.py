from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class ImportBatch(Base):
    __tablename__ = "import_batch"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    loai: Mapped[str] = mapped_column(String(30))
    ten_tep: Mapped[str] = mapped_column(String(300))
    rows: Mapped[list] = mapped_column(JSONType, default=list)
    loi: Mapped[list] = mapped_column(JSONType, default=list)
    trang_thai: Mapped[str] = mapped_column(String(20), default="xem_truoc")  # xem_truoc | da_nhap
    nguoi_tao_id: Mapped[int] = mapped_column(Integer)
    tao_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
