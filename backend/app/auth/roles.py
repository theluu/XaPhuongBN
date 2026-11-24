"""Vai trò và quyền mặc định (DT III.2, IV.2: phân quyền đọc/nhập/duyệt theo chức trách)."""

NHOM_DU_LIEU = [
    "ktxh", "dan_cu", "ngan_sach", "dau_tu_cong", "cong_trinh", "tthc_pakn", "gd_yt_mt", "canh_bao", "quan_tri", "he_thong",
]
NHOM_NHAY_CAM = {"ngan_sach", "dan_cu", "tthc_pakn"}
NHOM_NGHIEP_VU = [n for n in NHOM_DU_LIEU if n not in {"quan_tri", "he_thong"}]
NHOM_CONG_KHAI = [n for n in NHOM_NGHIEP_VU if n not in NHOM_NHAY_CAM]

ROLES = {
    "quan_tri_nen_tang": "Quản trị nền tảng",
    "quan_tri_don_vi": "Quản trị đơn vị",
    "lanh_dao": "Lãnh đạo",
    "xac_nhan": "Cán bộ xác nhận",
    "nhap_lieu": "Cán bộ nhập liệu",
    "chuyen_nganh": "Cơ quan chuyên ngành",
    "nguoi_xem": "Người xem",
    "man_hinh_tv": "Màn hình TV phòng điều hành",
}
ROLES_2FA = {"lanh_dao", "xac_nhan", "quan_tri_nen_tang", "quan_tri_don_vi"}
# Vai trò quản trị đơn vị được phép tạo (không bao giờ tạo được quản trị nền tảng)
UNIT_CREATABLE = {"lanh_dao", "xac_nhan", "nhap_lieu", "chuyen_nganh", "nguoi_xem", "man_hinh_tv", "quan_tri_don_vi"}
# Tài khoản các vai trò này do quản trị tạo phải được lãnh đạo đơn vị phê duyệt (tách nhiệm)
NEED_LEADER_APPROVAL = {"lanh_dao", "quan_tri_don_vi"}
ALL = ["doc", "nhap", "duyet"]


def default_grants(role: str, nhom: list[str] | None = None) -> list[tuple[list[str] | None, list[str]]]:
    """Trả về danh sách (nhóm dữ liệu | None = mọi nhóm, quyền)."""
    if role not in ROLES:
        raise ValueError(f"Vai trò không hợp lệ: {role}")
    if role == "quan_tri_nen_tang":
        return [(["he_thong"], ALL)]
    if role == "quan_tri_don_vi":
        return [(["quan_tri"], ALL), (NHOM_CONG_KHAI, ["doc"])]
    if role == "lanh_dao":
        return [(NHOM_NGHIEP_VU, ["doc"]), (["canh_bao"], ALL)]
    if role == "nguoi_xem":
        return [(NHOM_CONG_KHAI, ["doc"])]
    if role == "man_hinh_tv":  # xem phản ánh, cảnh báo ở dạng tổng hợp; không bao giờ thấy thông tin người gửi
        return [([*NHOM_CONG_KHAI, "tthc_pakn"], ["doc"])]
    if not nhom:
        raise ValueError("Vai trò này cần chỉ rõ nhóm dữ liệu")
    bad = [n for n in nhom if n not in NHOM_NGHIEP_VU]
    if bad:
        raise ValueError(f"Nhóm dữ liệu không hợp lệ: {', '.join(bad)}")
    if role == "xac_nhan":
        return [(nhom, ["doc", "duyet"])]
    if role == "nhap_lieu":
        return [(nhom, ["doc", "nhap"])]
    return [(nhom, ALL)]  # chuyen_nganh
