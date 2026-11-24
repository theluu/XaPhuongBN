"""Phản ánh hiện trường minh họa: đủ các trạng thái, có việc khẩn cấp, quá hạn, đến hạn hôm nay và phản ánh chưa có tọa độ."""
import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.field_reports.models import FieldReport
from app.platform.models import ResidentialGroup
from seeds.sample import ho_so

# (tiêu đề, lĩnh vực, khẩn cấp, ngày tiếp nhận trước hôm nay, hạn so với hôm nay, trạng thái, có tọa độ)
CASES = [
    ("Cây xanh đổ chắn ngang đường sau mưa lớn", "thien_tai", True, 0, 0, "da_giao", True),
    ("Vỡ đường ống cấp nước, nước tràn mặt đường", "ha_tang", True, 0, 1, "moi", True),
    ("Tụ tập gây mất trật tự khu vực chợ đêm", "an_ninh", True, 1, -0, "dang_xu_ly", True),
    ("Rác thải tồn đọng tại điểm tập kết đầu ngõ", "moi_truong", False, 6, -3, "dang_xu_ly", True),
    ("Đèn chiếu sáng công cộng hỏng cả tuyến", "ha_tang", False, 12, -5, "da_giao", True),
    ("Lấn chiếm vỉa hè làm nơi kinh doanh", "trat_tu_do_thi", False, 5, -2, "da_giao", True),
    ("Xây dựng công trình khi chưa có giấy phép", "xay_dung", False, 9, -4, "dang_xu_ly", False),
    ("Nắp hố ga bị vỡ, nguy hiểm cho người đi đường", "ha_tang", False, 3, 0, "da_giao", True),
    ("Đổ trộm phế thải xây dựng ven kênh", "moi_truong", False, 2, 0, "dang_xu_ly", True),
    ("Biển quảng cáo lắp đặt trái phép", "trat_tu_do_thi", False, 1, 2, "moi", True),
    ("Tiếng ồn từ xưởng sản xuất ban đêm", "moi_truong", False, 1, 2, "moi", False),
    ("Đường nội đồng sạt lở sau mưa", "ha_tang", False, 4, 3, "dang_xu_ly", True),
    ("Hộ nghèo cần hỗ trợ sửa nhà", "an_sinh", False, 3, 4, "da_giao", True),
    ("Tranh chấp ranh giới đất giữa hai hộ", "dat_dai", False, 8, 2, "cho_xac_nhan", False),
    ("Cống thoát nước bị tắc gây ngập cục bộ", "ha_tang", False, 15, -8, "hoan_thanh", True),
    ("Chó thả rông không rọ mõm", "an_ninh", False, 20, -15, "hoan_thanh", True),
    ("Đốt rơm rạ gây khói", "moi_truong", False, 10, -6, "hoan_thanh", True),
    ("Đề nghị bổ sung thùng rác công cộng", "moi_truong", False, 0, 3, "moi", True),
]
# Cán bộ phụ trách theo đơn vị (khớp danh bạ minh họa seeds/sample/org.py)
NGUOI = {"KTHTDT": ["Nguyễn Văn An", "Trần Thị Bích", "Lê Quang Huy"], "CA": ["Thiếu tá Nguyễn Đức Long"], "QS": ["Trương Văn Kiên"],
         "VHXH": ["Hà Văn Quân", "Mai Thị Thu"], "VP": ["Đinh Quang Vinh"]}
TEN_DUONG = ["đường Nguyễn Thế Nho", "đường Hoàng Hoa Thám", "phố Bích Sơn", "ngõ 12 Tự Lạn", "đường Thân Nhân Trung", "khu dân cư Đồng Cửa"]


def _r(*p: object) -> int:
    return int(hashlib.md5("|".join(map(str, p)).encode()).hexdigest()[:6], 16)


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    P = ho_so.P
    today = date.today()
    cases = [c for i, c in enumerate(CASES, start=1) if i not in P.bo_phan_anh] + P.them_phan_anh
    duong = P.ten_duong or TEN_DUONG
    tdps = list((await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == tenant_id).order_by(ResidentialGroup.ma_tdp))).scalars())
    pb = {"thien_tai": "QS", "an_ninh": "CA", "an_sinh": "VHXH", "khac": "VP"}
    for i, (ten, lv, khan, nhan, han, tt, toa_do) in enumerate(cases, start=1):
        r = _r("pa", P.muoi, i)
        g = tdps[i % len(tdps)] if tdps else None
        recv = datetime.now(UTC) - timedelta(days=nhan, hours=r % 9)
        lich_su = [{"luc": recv.isoformat(), "nguoi": P.tk("canbo1"), "hanh_dong": "tiep_nhan", "nguon": "duong_day_nong"}]
        if tt != "moi":
            lich_su.append({"luc": (recv + timedelta(hours=2)).isoformat(), "nguoi": P.tk("chutich"), "hanh_dong": "giao_xu_ly",
                            "han": (today + timedelta(days=han)).isoformat()})
        if tt in ("dang_xu_ly", "cho_xac_nhan", "hoan_thanh"):
            lich_su.append({"luc": (recv + timedelta(hours=20)).isoformat(), "nguoi": P.tk("canbo1"), "hanh_dong": "cap_nhat_tien_do", "tien_do": 50,
                            "ghi_chu": "Đã cử cán bộ kiểm tra hiện trường, lập biên bản"})
        if tt in ("cho_xac_nhan", "hoan_thanh"):
            lich_su.append({"luc": (recv + timedelta(days=2)).isoformat(), "nguoi": P.tk("canbo1"), "hanh_dong": "bao_cao_hoan_thanh", "ghi_chu": "Đã xử lý xong"})
        if tt == "hoan_thanh":
            lich_su.append({"luc": (recv + timedelta(days=2, hours=3)).isoformat(), "nguoi": P.tk("chutich"), "hanh_dong": "xac_nhan_hoan_thanh"})
        s.add(FieldReport(
            tenant_id=tenant_id, ma=f"PA-{today.year}-{9000 + i}", tieu_de=ten, mo_ta=f"{ten}. Người dân phản ánh qua đường dây nóng, đề nghị phường xử lý.",
            linh_vuc=lv, nguon=["duong_day_nong", "ung_dung", "can_bo", "truc_tiep"][r % 4], khan_cap=khan, tdp_id=g.id if g else None,
            dia_chi=f"{duong[r % len(duong)]}, {g.ten if g else ''}".strip(", "),
            lat=Decimal(str(P.lat(round(21.255 + (r % 350) / 10000, 6)))) if toa_do else None,
            lng=Decimal(str(P.lng(round(106.075 + (r // 7 % 500) / 10000, 6)))) if toa_do else None,
            anh_keys=[], nguoi_gui_ten=f"Công dân {i:02d}", nguoi_gui_sdt=f"09{r % 100000000:08d}",
            don_vi_phu_trach=None if tt == "moi" else pb.get(lv, "KTHTDT"), nguoi_phu_trach=None if tt == "moi" else P.nguoi(NGUOI[pb.get(lv, "KTHTDT")][r % len(NGUOI[pb.get(lv, "KTHTDT")])]),
            chi_dao="" if tt == "moi" else "Kiểm tra, xử lý dứt điểm và báo cáo kết quả", han_xu_ly=today + timedelta(days=han),
            trang_thai=tt, tien_do_pct={"moi": 0, "da_giao": 0, "dang_xu_ly": 50}.get(tt, 100),
            ket_qua="Đã xử lý xong, hiện trường đã được khắc phục" if tt in ("cho_xac_nhan", "hoan_thanh") else "",
            anh_ket_qua_keys=[], tiep_nhan_luc=recv, hoan_thanh_luc=recv + timedelta(days=2, hours=3) if tt == "hoan_thanh" else None,
            nguoi_tiep_nhan_id=users.get("canbo1"), lich_su=lich_su, is_sample=True,
        ))
