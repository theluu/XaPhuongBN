"""Chu kỳ cập nhật đề xuất — chép từ bảng DT III.3."""

DEFAULT_CYCLES: dict[str, dict] = {
    "ktxh": {"ky": ["thang", "quy", "nam"], "dieu_kien": "Theo kỳ báo cáo chính thức; phường ký xác nhận", "can_xac_nhan": True},
    "dan_cu": {"ky": ["thang"], "dieu_kien": "Chỉ nhận bản tổng hợp theo phường nếu có và được phép", "can_xac_nhan": True},
    "ngan_sach": {"ky": ["tuan", "thang"], "dieu_kien": "Sở Tài chính và phường đối soát theo kỳ chốt", "can_xac_nhan": True},
    "dau_tu_cong": {"ky": ["tuan"], "dieu_kien": "Chủ đầu tư/đơn vị phụ trách xác nhận giải ngân và tiến độ", "can_xac_nhan": True},
    "cong_trinh": {"ky": ["tuan"], "dieu_kien": "Chủ đầu tư/cơ quan chủ quản xác nhận và có minh chứng",
                   "can_xac_nhan": True, "can_minh_chung": True},
    "tthc_pakn": {"ky": ["api", "ky_bao_cao"], "dieu_kien": "API và TTHC theo báo cáo kỳ", "can_xac_nhan": True},
    "gd_yt_mt": {"ky": ["thang", "quy"], "dieu_kien": "Đơn vị chuyên ngành xác nhận nguồn và phạm vi", "can_xac_nhan": True},
}
