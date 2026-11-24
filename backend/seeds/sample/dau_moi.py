"""Người liên hệ và tài khoản minh họa của các đầu mối (DT V.1). Tên, số điện thoại là giả định.
Cán bộ cấp thành phố/sở ngành phụ trách nhiều phường nên tên liên hệ giống nhau giữa các phường; tài khoản tách theo phường."""
from sqlalchemy import select

from app.auth.models import Grant
from app.dau_moi.service import ensure
from app.platform.models import Tenant
from seeds.sample import ho_so

# mã đầu mối: (người liên hệ, chức vụ, điện thoại, email, [khóa tài khoản trong kịch bản])
LIEN_HE = {
    "UBND": (None, "Chủ tịch UBND", None, None, ["chutich", "xacnhan", "ketoan", "qtphuong"]),
    "VPDU": (None, "Bí thư Đảng ủy", None, None, ["bithu"]),
    "HCC": (None, "Chuyên viên tiếp nhận – trả kết quả", None, None, ["canbo1"]),
    "SOKHCN": ("Nguyễn Minh Tuấn", "Phó Giám đốc Trung tâm Chuyển đổi số", "0222 3822 610", "ioc@sokhcn.bacninh.gov.vn", ["@nentang"]),
    "VPUBNDTP": ("Trần Thị Lan Anh", "Phó Chánh Văn phòng", "0222 3822 300", "vpubnd@bacninh.gov.vn", []),
    "STC": ("Lê Văn Hùng", "Trưởng phòng Quản lý ngân sách", "0222 3822 455", "qlns@stc.bacninh.gov.vn", ["sotaichinh"]),
    "KBNN": ("Phạm Thị Hương", "Trưởng phòng Kiểm soát chi", "0222 3822 512", "kiemsoatchi@kbnn.bacninh.gov.vn", ["khobac"]),
    "THUE": ("Đỗ Quang Minh", "Đội trưởng Đội Thuế liên phường", "0222 3822 701", "doithue@thue.bacninh.gov.vn", ["thue"]),
    "CATP": ("Thiếu tá Hoàng Văn Nam", "Phó Đội trưởng Đội Quản lý cư trú", "0222 3822 113", "cutru@catp.bacninh.gov.vn", ["congan"]),
    "SXD": ("Ngô Thị Thanh", "Phó Trưởng phòng Quản lý xây dựng", "0222 3822 820", "qlxd@sxd.bacninh.gov.vn", ["soxaydung"]),
    "BQLDA": ("Vũ Đình Khoa", "Phó Giám đốc Ban QLDA ĐTXD", "0222 3822 930", "banqlda@bacninh.gov.vn", ["banqlda"]),
    "SGDDT": ("Bùi Thị Hạnh", "Chuyên viên Phòng Kế hoạch – Tài chính", "0222 3822 640", "khtc@sgddt.bacninh.gov.vn", ["sogddt"]),
    "BHXH": ("Đặng Văn Lộc", "Trưởng phòng Quản lý thu", "0222 3822 560", "qlthu@bhxh.bacninh.gov.vn", ["bhxh"]),
    "MTCN": ("Nguyễn Thị Hòa", "Phó Giám đốc Công ty cấp thoát nước", "0222 3822 870", "capnuoc@bacninh.example", ["moitruong"]),
    "THONGKE": ("Trịnh Văn Hải", "Thống kê viên", "0222 3822 480", "thongke@bacninh.gov.vn", ["thongke"]),
    "PAKN": ("Lý Thị Thu", "Chuyên viên Trung tâm Giám sát điều hành", "0222 3822 615", "pakn@bacninh.gov.vn", []),
}


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    from app.auth.models import User

    P = ho_so.P
    t = await s.get(Tenant, tenant_id)
    nen_tang = (await s.execute(select(Grant.user_id).where(Grant.role == "quan_tri_nen_tang").order_by(Grant.user_id))).scalars().first()
    rows = {d.ma: d for d in await ensure(s, tenant_id, t.ten)}
    names = {u.id: u for u in (await s.execute(select(User).where(User.id.in_([i for i in users.values() if i])))).scalars()}
    for ma, (ten, cv, dt, email, keys) in LIEN_HE.items():
        d = rows.get(ma)
        if d is None:
            continue
        ids = [nen_tang if k == "@nentang" else users.get(k) for k in keys]
        ids = [i for i in ids if i]
        first = names.get(ids[0]) if ids and ids[0] in names else None
        d.nguoi_lien_he = ten or (first.ho_ten if first else "")
        d.chuc_vu = cv
        d.dien_thoai = dt or (f"{P.dt_don_vi} 100" if d.cap == "phuong" else None)
        d.email = email or f"{ma.lower()}.{P.slug}@bacninh.gov.vn"
        d.user_ids = ids
        d.is_sample = True
    await s.flush()
