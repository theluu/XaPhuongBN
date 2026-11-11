from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class PointOfInterest(Base):
    """Điểm trường, trạm y tế, điểm môi trường — chỉ hiển thị khi được phép và dữ liệu đạt chất lượng (DT II.7)."""

    __tablename__ = "point_of_interest"
    __table_args__ = {"info": {"rls": True}}

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    loai: Mapped[str] = mapped_column(String(30))  # truong | tram_y_te | diem_moi_truong
    ten: Mapped[str] = mapped_column(String(300))
    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    thuoc_tinh: Mapped[dict] = mapped_column(JSONType, default=dict)
    chat_luong_du_lieu: Mapped[str] = mapped_column(String(20), default="chua_dat")
    cho_phep_hien_thi: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
