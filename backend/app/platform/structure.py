"""Cơ cấu tổ chức mặc định của xã/phường theo mô hình chính quyền địa phương 2 cấp (từ 01/7/2025).

- Cơ quan chuyên môn thuộc UBND cấp xã (Nghị định 150/2025/NĐ-CP): Văn phòng HĐND và UBND; Phòng Kinh tế
  (xã, đặc khu) hoặc Phòng Kinh tế, Hạ tầng và Đô thị (phường); Phòng Văn hóa – Xã hội.
- Trung tâm Phục vụ hành chính công cấp xã tiếp nhận, trả kết quả TTHC.
- Lực lượng phối hợp xử lý tại địa bàn: Công an, Ban Chỉ huy quân sự, Ủy ban MTTQ, Trạm y tế.
- Dưới cấp xã là thôn (xã) hoặc tổ dân phố (phường) — tổ chức tự quản, không phải cấp hành chính.

Đơn vị có thể sửa toàn bộ danh mục trong Quản trị → Danh mục.
"""

PHONG_BAN_XA = [
    {"ma": "VP", "ten": "Văn phòng HĐND và UBND", "loai": "chuyen_mon"},
    {"ma": "KT", "ten": "Phòng Kinh tế", "loai": "chuyen_mon"},
    {"ma": "VHXH", "ten": "Phòng Văn hóa – Xã hội", "loai": "chuyen_mon"},
    {"ma": "HCC", "ten": "Trung tâm Phục vụ hành chính công", "loai": "chuyen_mon"},
    {"ma": "CA", "ten": "Công an xã", "loai": "phoi_hop"},
    {"ma": "QS", "ten": "Ban Chỉ huy quân sự xã", "loai": "phoi_hop"},
    {"ma": "MTTQ", "ten": "Ủy ban MTTQ Việt Nam xã", "loai": "phoi_hop"},
    {"ma": "YT", "ten": "Trạm Y tế", "loai": "phoi_hop"},
]

PHONG_BAN_PHUONG = [
    {"ma": "VP", "ten": "Văn phòng HĐND và UBND", "loai": "chuyen_mon"},
    {"ma": "KTHTDT", "ten": "Phòng Kinh tế, Hạ tầng và Đô thị", "loai": "chuyen_mon"},
    {"ma": "VHXH", "ten": "Phòng Văn hóa – Xã hội", "loai": "chuyen_mon"},
    {"ma": "HCC", "ten": "Trung tâm Phục vụ hành chính công", "loai": "chuyen_mon"},
    {"ma": "CA", "ten": "Công an phường", "loai": "phoi_hop"},
    {"ma": "QS", "ten": "Ban Chỉ huy quân sự phường", "loai": "phoi_hop"},
    {"ma": "MTTQ", "ten": "Ủy ban MTTQ Việt Nam phường", "loai": "phoi_hop"},
    {"ma": "YT", "ten": "Trạm Y tế", "loai": "phoi_hop"},
]

# Lĩnh vực phản ánh hiện trường và đơn vị chủ trì mặc định
LINH_VUC = [
    {"ma": "moi_truong", "ten": "Môi trường, rác thải", "chu_tri": "KT", "han_ngay": 3},
    {"ma": "trat_tu_do_thi", "ten": "Trật tự đô thị, lấn chiếm vỉa hè", "chu_tri": "KT", "han_ngay": 3},
    {"ma": "ha_tang", "ten": "Hạ tầng, đường, chiếu sáng, thoát nước", "chu_tri": "KT", "han_ngay": 7},
    {"ma": "xay_dung", "ten": "Xây dựng không phép, sai phép", "chu_tri": "KT", "han_ngay": 5},
    {"ma": "dat_dai", "ten": "Đất đai", "chu_tri": "KT", "han_ngay": 10},
    {"ma": "an_ninh", "ten": "An ninh trật tự", "chu_tri": "CA", "han_ngay": 1},
    {"ma": "an_sinh", "ten": "An sinh xã hội, y tế, giáo dục", "chu_tri": "VHXH", "han_ngay": 7},
    {"ma": "thien_tai", "ten": "Thiên tai, sự cố khẩn cấp", "chu_tri": "QS", "han_ngay": 1},
    {"ma": "khac", "ten": "Khác", "chu_tri": "VP", "han_ngay": 7},
]

NGUON_TIEP_NHAN = {
    "truc_tiep": "Trực tiếp tại Trung tâm Phục vụ HCC",
    "duong_day_nong": "Đường dây nóng",
    "ung_dung": "Ứng dụng/Zalo của phường, xã",
    "cong_dvc": "Cổng Dịch vụ công",
    "can_bo": "Cán bộ, tổ trưởng phát hiện",
    "camera": "Camera giám sát",
}


def dia_ban_label(cap: str) -> str:
    """Tên gọi đơn vị tự quản dưới cấp xã."""
    return "Tổ dân phố" if cap == "phuong" else "Thôn"


def default_phong_ban(cap: str) -> list[dict]:
    return [dict(r) for r in (PHONG_BAN_PHUONG if cap == "phuong" else PHONG_BAN_XA)]


def default_linh_vuc(cap: str) -> list[dict]:
    kt = "KTHTDT" if cap == "phuong" else "KT"
    return [{**r, "chu_tri": kt if r["chu_tri"] == "KT" else r["chu_tri"]} for r in LINH_VUC]


def phong_ban(cfg: dict, cap: str) -> list[dict]:
    return list(cfg.get("phong_ban") or default_phong_ban(cap))


def linh_vuc(cfg: dict, cap: str) -> list[dict]:
    return list(cfg.get("linh_vuc_phan_anh") or default_linh_vuc(cap))
