"""Lịch công tác tuần và văn bản chỉ đạo điều hành minh họa (nội dung, số hiệu giả định)."""
from datetime import date, timedelta

from app.lich.models import LichCongTac
from app.van_ban.models import VanBan
from seeds.sample import ho_so

# (thứ trong tuần 0=Thứ Hai, giờ bắt đầu, giờ kết thúc, nội dung, chủ trì (họ tên gốc), địa điểm, thành phần, chuẩn bị, loại, trạng thái)
LICH = [
    (0, "07:30", "09:00", "Giao ban lãnh đạo UBND đầu tuần: rà soát nhiệm vụ quá hạn, phản ánh khẩn cấp", "Lê Minh Châu", "Phòng họp tầng 2",
     "Các Phó Chủ tịch UBND, Trưởng các phòng chuyên môn", "Văn phòng HĐND và UBND", "hop", "chinh_thuc"),
    (0, "14:00", "16:30", "Kiểm tra tiến độ công trình đường trục chính tổ dân phố số 3–5", "Hoàng Văn Đức", "Hiện trường công trình",
     "Phòng Kinh tế, Hạ tầng và Đô thị; nhà thầu", "Phòng Kinh tế, Hạ tầng và Đô thị", "kiem_tra", "chinh_thuc"),
    (1, "08:00", "11:00", "Tiếp công dân định kỳ", "Lê Minh Châu", "Trụ sở tiếp công dân", "Công chức tư pháp, địa chính", "Văn phòng HĐND và UBND", "tiep_dan", "chinh_thuc"),
    (2, "08:00", "10:00", "Họp Ban Chỉ đạo giải phóng mặt bằng các dự án trọng điểm", "Hoàng Văn Đức", "Phòng họp tầng 2",
     "Tổ công tác GPMB, đại diện chủ đầu tư", "Phòng Kinh tế, Hạ tầng và Đô thị", "hop", "chinh_thuc"),
    (2, "14:00", "16:00", "Làm việc với Bảo hiểm xã hội về tỷ lệ tham gia BHYT", "Ngô Thị Lan", "Phòng họp tầng 1", "Phòng Văn hóa – Xã hội; BHXH", "Phòng Văn hóa – Xã hội", "lam_viec", "chinh_thuc"),
    (3, "08:00", "11:30", "Dự Hội nghị trực tuyến của thành phố về giải ngân vốn đầu tư công", "Lê Minh Châu", "Điểm cầu UBND phường", "Lãnh đạo UBND, Phòng Kinh tế", "Văn phòng HĐND và UBND", "hop", "chinh_thuc"),
    (3, "14:00", None, "Tập huấn sử dụng hệ thống điều hành số cho cán bộ các phòng", "Nguyễn Thị Hà", "Hội trường", "Cán bộ, công chức các phòng", "Văn phòng HĐND và UBND", "khac", "du_kien"),
    (4, "08:00", "10:00", "Họp Đảng ủy thường kỳ", "Trần Văn Bình", "Phòng họp Đảng ủy", "Ban Thường vụ Đảng ủy", "Văn phòng Đảng ủy", "hop", "chinh_thuc"),
    (4, "15:00", "17:00", "Đối thoại với hộ dân về phương án bồi thường dự án nhà văn hóa", "Hoàng Văn Đức", "Nhà văn hóa tổ dân phố số 8", "Tổ công tác GPMB, hộ dân", "Phòng Kinh tế, Hạ tầng và Đô thị", "lam_viec", "hoan"),
]
# (số ký hiệu, ngày trước hôm nay, loại, cơ quan, người ký (gốc), trích yếu, hạn thực hiện so với hôm nay, gắn nhiệm vụ mẫu)
VAN_BAN = [
    ("{n}/TB-UBND", 4, "thong_bao", "UBND {dv}", "Lê Minh Châu", "Kết luận của Chủ tịch UBND tại cuộc họp giao ban về thu ngân sách và giải ngân vốn đầu tư công", 5, True),
    ("{n2}/KH-UBND", 30, "ke_hoach", "UBND {dv}", "Lê Minh Châu", "Kế hoạch thực hiện các chỉ tiêu phát triển kinh tế – xã hội năm 2026", 50, False),
    ("01-NQ/ĐU", 460, "nghi_quyet", "Đảng ủy {dv}", "Trần Văn Bình", "Nghị quyết Đại hội đại biểu Đảng bộ phường lần thứ I, nhiệm kỳ 2025–2030", None, False),
    ("{n3}/CT-UBND", 60, "chi_thi", "UBND {dv}", "Lê Minh Châu", "Chỉ thị về tăng cường quản lý trật tự đô thị, vệ sinh môi trường trên địa bàn", 30, False),
    ("{n4}/UBND-KTHTDT", 10, "cong_van", "UBND {dv}", "Hoàng Văn Đức", "Đôn đốc chủ đầu tư cập nhật khối lượng, giải ngân hằng tuần trên hệ thống điều hành", 14, True),
]


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    P = ho_so.P
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    for thu, bd, kt, nd, ct, dd, tp, cb, loai, tt in LICH:
        s.add(LichCongTac(tenant_id=tenant_id, ngay=monday + timedelta(days=thu), gio_bat_dau=bd, gio_ket_thuc=kt, noi_dung=P.chu(nd), chu_tri=P.nguoi(ct),
                          dia_diem=dd, thanh_phan=tp, don_vi_chuan_bi=cb, loai=loai, trang_thai=tt, hien_tren_tv=True, ghi_chu="", is_sample=True))
    dv = f"phường {P.ten}"
    base = 100 + len(P.muoi) * 7
    for i, (so, truoc, loai, cq, nk, ty, han, gan) in enumerate(VAN_BAN):
        s.add(VanBan(tenant_id=tenant_id, so_ky_hieu=so.format(n=base + 87, n2=base + 12, n3=base + 3, n4=base + 141), ngay_ban_hanh=today - timedelta(days=truoc),
                     loai=loai, co_quan_ban_hanh=cq.format(dv=dv), nguoi_ky=P.nguoi(nk), trich_yeu=ty, file_key=None, lien_ket=None,
                     han_thuc_hien=today + timedelta(days=han) if han is not None else None, trang_thai="con_hieu_luc",
                     nhiem_vu_ids=["__gan__"] if gan else [], is_sample=True))
