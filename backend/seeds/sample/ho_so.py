"""Hồ sơ đơn vị dùng khi sinh dữ liệu minh họa: cùng bộ kịch bản nhưng mỗi phường có tên, vị trí, quy mô, cán bộ
và tình huống khác nhau, để thấy dữ liệu các đơn vị tách biệt. Tên người, số điện thoại đều là giả định."""
from dataclasses import dataclass, field

GOC = "Việt Yên"


@dataclass
class HoSo:
    ten: str = GOC                      # tên riêng của phường
    slug: str = "vietyen"               # dùng cho email minh họa
    tien_to: str = ""                   # tiền tố tên đăng nhập (VD "nenh.")
    dlat: float = 0.0                   # dịch tọa độ so với bộ gốc (Việt Yên)
    dlng: float = 0.0
    dan_so: int = 51_200
    he_so_thu: dict[str, float] = field(default_factory=dict)   # nhóm thu → hệ số thực hiện thay thế
    he_so_du_toan: float = 1.0
    chi_tieu: dict[str, dict[str, float]] = field(default_factory=dict)  # ghi đè chuỗi số liệu chỉ tiêu
    doi_ten: dict[str, str] = field(default_factory=dict)      # họ tên cán bộ gốc → họ tên ở phường này
    to_truong: list[str] | None = None
    ten_duong: list[str] | None = None
    dt_don_vi: str = "0222 3874"
    muoi: str = ""                      # thay đổi phân bố ngẫu nhiên có kiểm soát
    bo_phan_anh: set[int] = field(default_factory=set)         # số thứ tự phản ánh gốc bỏ qua
    them_phan_anh: list[tuple] = field(default_factory=list)
    tai_khoan: dict[str, str] = field(default_factory=dict)    # vai trò kịch bản → tên đăng nhập thật

    def tk(self, key: str) -> str:
        return self.tai_khoan.get(key, self.tien_to + key)

    def nguoi(self, ho_ten: str) -> str:
        return self.doi_ten.get(ho_ten, ho_ten)

    def chu(self, s: str) -> str:
        return s.replace(GOC, self.ten).replace(GOC.upper(), self.ten.upper())

    def lat(self, x: float | None) -> float | None:
        return None if x is None else round(x + self.dlat, 6)

    def lng(self, x: float | None) -> float | None:
        return None if x is None else round(x + self.dlng, 6)


NENH = HoSo(
    ten="Nếnh", slug="nenh", tien_to="nenh.", dlat=-0.0345, dlng=-0.0125, dan_so=68_400,
    # Phường công nghiệp: thu thuế CTN và TNCN cao, tiền sử dụng đất đạt tiến độ
    he_so_thu={"THUE_CTN": 1.12, "THUE_TNCN": 1.15, "TIEN_SDD": 0.97}, he_so_du_toan=1.3,
    chi_tieu={
        "NQ01-03b": {"2024": 86.0, "2025": 88.5},                 # không còn nguy cơ
        "NQ01-08a": {"2024": 29.1, "2025": 30.2},
        "NQ01-10": {"2025-Q3": 74, "2025-Q4": 71, "2026-Q1": 69, "2026-Q2": 66, "2026-Q3": 63},  # nhà tạm còn nhiều (khu trọ công nhân)
        "NQ01-16": {"2025-Q3": 9.6, "2026-Q1": 10.1, "2026-Q2": 10.4, "2026-Q3": 10.8},
        "DT-TRUONG": {"2024": 11, "2025": 12}, "DT-LOP": {"2024": 302, "2025": 318}, "DT-HS": {"2024": 11120, "2025": 11870},
    },
    doi_ten={
        "Trần Văn Bình": "Nguyễn Hữu Thắng", "Lê Minh Châu": "Đào Thị Phương", "Hoàng Văn Đức": "Phạm Quốc Toản",
        "Ngô Thị Lan": "Trịnh Thị Huế", "Nguyễn Thị Hà": "Lê Văn Khánh", "Phạm Thu Dung": "Nguyễn Thị Oanh",
        "Vũ Thị Giang": "Hoàng Thị Thủy", "Nguyễn Văn An": "Tạ Văn Hưng", "Trần Thị Bích": "Dương Thị Nhung",
        "Lê Quang Huy": "Nguyễn Đình Phong", "Mai Thị Thu": "Vi Thị Hằng", "Hà Văn Quân": "Lưu Văn Tú",
        "Đỗ Thị Mai": "Kiều Thị Thanh", "Thiếu tá Nguyễn Đức Long": "Trung tá Thân Văn Hùng", "Trương Văn Kiên": "Giáp Văn Lực",
        "Lương Thị Hạnh": "Ngô Thị Hảo", "BS. Cao Văn Phúc": "BS. Hà Thị Liên", "Đinh Quang Vinh": "Chu Văn Định",
        "Đặng Thị Hồng": "Nguyễn Văn Quyết", "Phan Văn Khải": "Thân Thị Hoa", "Bùi Thị Ngọc": "Lê Văn Sáng",
        "Lý Văn Tâm": "Đỗ Văn Chiến", "Vương Văn Sơn": "Nguyễn Thị Lựu",
    },
    to_truong=["Thân Văn Mạnh", "Nguyễn Thị Gấm", "Đỗ Văn Hòa", "Giáp Thị Nhàn", "Ngô Văn Thiệp", "Trần Văn Lâm",
               "Nguyễn Văn Đoàn", "Lê Thị Huyền", "Hoàng Văn Tráng"],
    ten_duong=["đường Quốc lộ 37", "đường gom Quốc lộ 1", "khu nhà trọ công nhân Ninh Khánh", "đường vào KCN Đình Trám", "phố Nếnh", "khu dân cư Ninh Động"],
    dt_don_vi="0222 3866", muoi="nenh", bo_phan_anh={12, 13, 16},
    them_phan_anh=[
        ("Nước thải từ khu công nghiệp chảy tràn ra mương tiêu", "moi_truong", True, 0, 0, "da_giao", True),
        ("Ùn tắc giờ tan ca trước cổng khu công nghiệp", "trat_tu_do_thi", False, 2, -1, "dang_xu_ly", True),
        ("Khu nhà trọ công nhân đấu nối điện không an toàn", "an_ninh", False, 1, 1, "moi", True),
        ("Xe tải chở vật liệu làm rơi vãi đất cát", "moi_truong", False, 3, -2, "da_giao", True),
        ("Người lao động ngoại tỉnh chưa khai báo tạm trú", "an_ninh", False, 4, 2, "dang_xu_ly", False),
    ],
)

HO_SO = {"viet_yen": HoSo(), "nenh": NENH}
MA_DVHC = {"P-VIETYEN": "viet_yen", "P-NENH": "nenh"}
TAM_GOC = (21.2725, 106.0975)

# Hồ sơ đang dùng trong lượt sinh dữ liệu hiện tại (seeds.run gán trước khi gọi các phân hệ)
P: HoSo = HoSo()


def chon(code: str) -> HoSo:
    global P
    P = HO_SO.get(code, HoSo())
    return P


def _slug(ten: str) -> str:
    import re
    import unicodedata

    t = unicodedata.normalize("NFD", ten.replace("đ", "d").replace("Đ", "D"))
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if unicodedata.category(c) != "Mn").lower()) or "donvi"


def cho_don_vi(ma_dvhc: str, ten: str, config: dict, tai_khoan: dict[str, str]) -> HoSo:
    """Hồ sơ cho đơn vị bất kỳ (VD phường mới khởi tạo): tên riêng, vị trí theo tâm bản đồ, phân bố riêng theo mã."""
    global P
    if ma_dvhc in MA_DVHC:
        P = HO_SO[MA_DVHC[ma_dvhc]]
        P.tai_khoan = tai_khoan
        return P
    rieng = ten.removeprefix("Phường ").removeprefix("Xã ").strip() or ten
    tam = (config.get("ban_do") or {}).get("tam") or TAM_GOC
    h = int.from_bytes(ma_dvhc.encode()[:4].ljust(4, b"0"), "big")
    P = HoSo(ten=rieng, slug=_slug(rieng), dlat=round(tam[0] - TAM_GOC[0], 6), dlng=round(tam[1] - TAM_GOC[1], 6),
             dan_so=30_000 + h % 40_000, he_so_du_toan=round(0.6 + (h % 90) / 100, 2), muoi=ma_dvhc,
             doi_ten={k: v for k, v in zip(NENH.doi_ten, [*list(NENH.doi_ten.values())[3:], *list(NENH.doi_ten.values())[:3]])},
             to_truong=NENH.to_truong[::-1], dt_don_vi=f"0222 38{h % 90 + 10:02d}", tai_khoan=tai_khoan)
    return P
