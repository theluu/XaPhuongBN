from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.platform.models import JSONType, tenant_fk


class OrgUnit(Base):
    """Đơn vị trong cơ cấu tổ chức của xã/phường (Đảng ủy, HĐND, UBND, cơ quan chuyên môn, MTTQ, lực lượng…).

    `ma` của cơ quan chuyên môn trùng mã phòng ban trong danh mục giao việc → đếm được việc đang xử lý theo đơn vị.
    """

    __tablename__ = "org_unit"
    __table_args__ = (UniqueConstraint("tenant_id", "ma"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma: Mapped[str] = mapped_column(String(20))
    ten: Mapped[str] = mapped_column(String(200))
    # dang | hdnd | ubnd | chuyen_mon | truc_thuoc | mttq | doan_the | luc_luong | phoi_hop
    khoi: Mapped[str] = mapped_column(String(20))
    cap_tren_ma: Mapped[str | None] = mapped_column(String(20), nullable=True)
    lanh_dao_phu_trach_ma: Mapped[str | None] = mapped_column(String(20), nullable=True)  # mã cán bộ (Phó Chủ tịch phụ trách khối)
    chuc_nang: Mapped[str] = mapped_column(Text, default="")
    dien_thoai: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dia_chi: Mapped[str | None] = mapped_column(String(300), nullable=True)
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)


class Staff(Base):
    """Cán bộ, công chức, người hoạt động không chuyên trách: chức vụ, liên hệ công vụ, phân công phụ trách."""

    __tablename__ = "org_staff"
    __table_args__ = (UniqueConstraint("tenant_id", "ma"), {"info": {"rls": True}})

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = tenant_fk()
    ma: Mapped[str] = mapped_column(String(20))
    don_vi_ma: Mapped[str] = mapped_column(String(20), index=True)
    ho_ten: Mapped[str] = mapped_column(String(200))
    chuc_vu: Mapped[str] = mapped_column(String(200))
    cap: Mapped[str] = mapped_column(String(20), default="thanh_vien")  # truong | pho | thanh_vien
    dien_thoai: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nhiem_vu: Mapped[str] = mapped_column(Text, default="")  # nội dung phân công
    linh_vuc: Mapped[list] = mapped_column(JSONType, default=list)  # mã lĩnh vực phản ánh phụ trách
    dia_ban_ids: Mapped[list] = mapped_column(JSONType, default=list)  # thôn/TDP được phân công theo dõi
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thu_tu: Mapped[int] = mapped_column(Integer, default=0)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
