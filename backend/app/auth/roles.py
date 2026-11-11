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
}
ROLES_2FA = {"lanh_dao", "xac_nhan", "quan_tri_nen_tang", "quan_tri_don_vi"}
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
        return [(None, ["doc"]), (["canh_bao"], ALL)]
    if role == "nguoi_xem":
        return [(NHOM_CONG_KHAI, ["doc"])]
    if not nhom:
        raise ValueError("Vai trò này cần chỉ rõ nhóm dữ liệu")
    if role == "xac_nhan":
        return [(nhom, ["doc", "duyet"])]
    if role == "nhap_lieu":
        return [(nhom, ["doc", "nhap"])]
    return [(nhom, ALL)]  # chuyen_nganh
