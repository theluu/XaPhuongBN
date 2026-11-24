from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class DauMoi(Base):
    """Đầu mối và trách nhiệm chủ trì/phối hợp theo dự thảo kịch bản (DT V.1, Phụ lục 02): UBND phường, Sở, ngành,
    chủ đầu tư… Mỗi đầu mối có trách nhiệm theo từng nhóm dữ liệu, chỉ tiêu/nguồn mình cung cấp – xác nhận,
    người liên hệ và các tài khoản trên hệ thống được gắn với đầu mối."""

    __tablename__ = "dau_moi"
    __table_args__ = (UniqueConstraint("tenant_id", "ma"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma: Mapped[str] = mapped_column(String(30))
    ten: Mapped[str] = mapped_column(String(300))
    cap: Mapped[str] = mapped_column(String(20))  # phuong | thanh_pho | chuyen_nganh | chu_dau_tu
    noi_dung: Mapped[str] = mapped_column(Text, default="")  # trách nhiệm chung (nguyên văn DT V.1 khi có)
    # [{nhom, vai_tro: chu_tri|phoi_hop|cung_cap|xac_nhan, noi_dung}]
    trach_nhiem: Mapped[list] = mapped_column(JSONType, default=list)
    phieu_nguon: Mapped[list] = mapped_column(JSONType, default=list)  # mục Phụ lục 02 (A–H)
    chi_tieu: Mapped[list] = mapped_column(JSONType, default=list)  # mã chỉ tiêu đầu mối cung cấp/xác nhận
    nguon: Mapped[list] = mapped_column(JSONType, default=list)  # mã nguồn dữ liệu (data_source.ma)
    nguoi_lien_he: Mapped[str] = mapped_column(String(200), default="")
    chuc_vu: Mapped[str] = mapped_column(String(200), default="")
    dien_thoai: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    user_ids: Mapped[list] = mapped_column(JSONType, default=list)  # tài khoản gắn với đầu mối
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
