from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class FieldReport(Base):
    """Phản ánh hiện trường: tiếp nhận → xác định địa điểm → giao đơn vị phụ trách → theo dõi hạn → xác nhận đã xử lý.

    Thông tin người gửi chỉ trả về cho cán bộ có quyền nhập/duyệt nhóm tthc_pakn, không bao giờ hiện trên màn hình TV.
    """

    __tablename__ = "field_report"
    __table_args__ = (UniqueConstraint("tenant_id", "ma"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma: Mapped[str] = mapped_column(String(40))
    tieu_de: Mapped[str] = mapped_column(String(300))
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    linh_vuc: Mapped[str] = mapped_column(String(40))
    nguon: Mapped[str] = mapped_column(String(30), default="truc_tiep")
    khan_cap: Mapped[bool] = mapped_column(Boolean, default=False)
    tdp_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    dia_chi: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    anh_keys: Mapped[list] = mapped_column(JSONType, default=list)
    nguoi_gui_ten: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nguoi_gui_sdt: Mapped[str | None] = mapped_column(String(30), nullable=True)
    don_vi_phu_trach: Mapped[str | None] = mapped_column(String(20), nullable=True)  # mã phòng ban
    nguoi_phu_trach: Mapped[str | None] = mapped_column(String(200), nullable=True)
    chi_dao: Mapped[str] = mapped_column(Text, default="")
    han_xu_ly: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    # moi | da_giao | dang_xu_ly | cho_xac_nhan | hoan_thanh | tu_choi
    trang_thai: Mapped[str] = mapped_column(String(20), default="moi", index=True)
    tien_do_pct: Mapped[int] = mapped_column(Integer, default=0)
    ket_qua: Mapped[str] = mapped_column(Text, default="")
    anh_ket_qua_keys: Mapped[list] = mapped_column(JSONType, default=list)
    tiep_nhan_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    hoan_thanh_luc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cap_nhat_luc: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    nguoi_tiep_nhan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lich_su: Mapped[list] = mapped_column(JSONType, default=list)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
