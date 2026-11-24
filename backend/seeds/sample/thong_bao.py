"""Thông báo điều hành minh họa cho dải bản tin (nội dung giả định)."""
from datetime import date, timedelta

from app.thong_bao.models import ThongBao
from seeds.sample import ho_so

TIN = [
    # (tiêu đề, mức độ, bắt đầu so với hôm nay, số ngày hiệu lực, ghim, đối tượng, liên kết)
    ("Giao ban UBND {dv} sáng thứ Hai, 08h00 tại phòng họp tầng 2: các phòng chuẩn bị báo cáo tiến độ nhiệm vụ quá hạn", "quan_trong", -1, 6, True, [], "/canh-bao"),
    ("Cảnh báo mưa lớn, nguy cơ ngập úng cục bộ: Ban Chỉ huy quân sự, tổ dân phố trực ứng phó 24/24", "khan", 0, 2, False, [], "/phan-anh"),
    ("Hạn nộp số liệu chỉ tiêu quý III: các đầu mối hoàn thành trước ngày 20 tháng sau kỳ", "thuong", -3, 14, False, ["nhap_lieu", "xac_nhan", "chuyen_nganh"], "/nhap-lieu?tab=tuan-thu"),
    ("Tập huấn sử dụng hệ thống điều hành số cho cán bộ các phòng, chiều thứ Tư", "thuong", -2, 7, False, [], None),
    ("Đẩy nhanh giải ngân vốn đầu tư công: chủ đầu tư cập nhật khối lượng, giải ngân hằng tuần", "quan_trong", -5, 20, False, ["lanh_dao", "chuyen_nganh", "xac_nhan"], "/dau-tu-cong"),
]


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    today = date.today()
    dv = f"phường {ho_so.P.ten}"
    for ten, muc, bd, n, ghim, dt, link in TIN:
        s.add(ThongBao(tenant_id=tenant_id, tieu_de=ten.format(dv=dv), noi_dung="", lien_ket=link, muc_do=muc, tu_ngay=today + timedelta(days=bd),
                       den_ngay=today + timedelta(days=bd + n), doi_tuong=dt, ghim=ghim, hien_tren_tv=True, nguoi_tao_id=users.get("chutich"), is_sample=True))
