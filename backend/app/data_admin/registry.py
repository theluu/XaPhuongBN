"""Danh mục bộ dữ liệu được quản lý tập trung: bảng nào, trường nào sửa được, kiểu dữ liệu, nhóm quyền, quy tắc xác nhận.

Mỗi bộ dữ liệu khai báo một lần ở đây; giao diện "Quản lý dữ liệu" và API /api/du-lieu dùng chung khai báo này."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class F:
    name: str
    label: str
    kind: str = "text"  # text | textarea | int | dec | date | datetime | time | bool | enum | multi | cat | ref | refmulti | file | ky
    required: bool = False
    options: dict[str, str] | None = None  # enum
    cat: str | None = None  # loại danh mục dùng chung (shared_catalog.loai)
    ref: str | None = None  # indicator | tdp | project | work | case
    readonly: bool = False  # chỉ hiển thị (trạng thái do quy trình quản lý)
    create_only: bool = False  # chỉ nhập khi tạo (mã định danh)
    list: bool = True  # hiện trên bảng
    help: str = ""


@dataclass(frozen=True)
class Confirm:
    """Bản ghi đã xác nhận/đối soát: sửa → quay về trạng thái chờ, phải xác nhận lại (không sửa ngầm số đã chốt)."""
    field: str
    locked: tuple[str, ...]
    reset_to: str
    clear: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dataset:
    key: str
    ten: str
    nhom_phan_he: str  # nhóm hiển thị trong menu
    model_path: str
    nhom: str  # nhóm quyền; "@indicator" = theo nhóm của chỉ tiêu; "a|b" = quyền quản trị trên một trong các nhóm
    fields: tuple[F, ...]
    order: tuple[str, ...] = ("id",)
    search: tuple[str, ...] = ()
    confirm: Confirm | None = None
    mo_ta: str = ""
    sample: bool = True  # có cột is_sample
    link: str | None = None  # trang nghiệp vụ liên quan
    defaults: dict[str, Any] = field(default_factory=dict)
    them: bool = True  # cho phép thêm mới tại đây
    them_link: str | None = None  # thêm mới tại màn hình nghiệp vụ (khi them=False)

    @property
    def model(self) -> Any:
        import importlib

        mod, cls = self.model_path.rsplit(".", 1)
        return getattr(importlib.import_module(mod), cls)


TT_XN = {"tam_thoi": "Tạm thời", "da_xac_nhan": "Đã xác nhận", "tu_choi": "Bị từ chối"}
KY_HELP = "Năm 2026, quý 2026-Q3, tháng 2026-10 hoặc tuần 2026-W40"

DATASETS: list[Dataset] = [
    # ---------------- Chỉ tiêu KT-XH ----------------
    Dataset("chi_tieu", "Danh mục chỉ tiêu", "Chỉ tiêu KT-XH", "app.catalog.models.Indicator", "quan_tri|canh_bao", (
        F("ma_chi_tieu", "Mã chỉ tiêu", required=True, create_only=True), F("ten", "Tên chỉ tiêu", required=True),
        F("nhom", "Nhóm dữ liệu", "enum", True, {"ktxh": "Kinh tế – xã hội", "dan_cu": "Dân cư", "ngan_sach": "Ngân sách", "dau_tu_cong": "Đầu tư công",
                                                 "cong_trinh": "Công trình", "tthc_pakn": "TTHC – PAKN", "gd_yt_mt": "GD – YT – MT"}),
        F("phan_he", "Phân hệ hiển thị", list=False), F("don_vi_do", "Đơn vị đo", required=True),
        F("dinh_nghia", "Định nghĩa", "textarea", list=False), F("cong_thuc", "Công thức tính", "textarea", list=False),
        F("pham_vi_dia_ban", "Phạm vi địa bàn", list=False),
        F("chieu", "Chiều đánh giá", "enum", options={"tang_tot": "Càng cao càng tốt", "giam_tot": "Càng thấp càng tốt", "dat_nguong": "Đạt ngưỡng", "theo_doi": "Chỉ theo dõi"}, list=False),
        F("muc_tieu", "Mục tiêu năm", "dec"), F("muc_tieu_2030", "Mục tiêu 2030", "dec"),
        F("nguon_mac_dinh", "Nguồn mặc định", list=False), F("don_vi_chu_quan", "Đơn vị chủ quản"),
        F("nguoi_xac_nhan_mac_dinh", "Người xác nhận mặc định", list=False),
        F("ky_cap_nhat", "Kỳ cập nhật", "enum", True, {"tuan": "Tuần", "thang": "Tháng", "quy": "Quý", "nam": "Năm", "api": "Theo API", "ky_bao_cao": "Theo kỳ báo cáo"}),
        F("han_cap_nhat_ngay", "Hạn nộp (ngày sau kỳ)", "int", list=False), F("can_minh_chung", "Cần minh chứng", "bool", list=False),
        F("phan_loai_thong_tin", "Phân loại thông tin", "enum", options={"cong_khai": "Công khai", "noi_bo": "Nội bộ", "han_che": "Hạn chế"}, list=False),
        F("ghi_chu", "Ghi chú", "textarea", list=False),
    ), order=("ma_chi_tieu",), search=("ma_chi_tieu", "ten", "don_vi_chu_quan"), sample=False, link="/chi-tieu",
        mo_ta="Hồ sơ chỉ tiêu (DT III.1). Sửa chỉ tiêu từ gói mẫu sẽ được giữ nguyên khi nâng cấp gói.",
        defaults={"dinh_nghia": "", "cong_thuc": "", "pham_vi_dia_ban": "Toàn phường", "phan_he": "ktxh", "chieu": "tang_tot", "nguon_mac_dinh": "",
                  "don_vi_chu_quan": "", "nguoi_xac_nhan_mac_dinh": "", "han_cap_nhat_ngay": 10, "dinh_dang": "so", "phan_loai_thong_tin": "noi_bo",
                  "can_minh_chung": False, "ghi_chu": "", "bo": [], "nguon_uu_tien": [], "luy_ke": False}),
    Dataset("ke_hoach", "Kế hoạch chỉ tiêu theo kỳ", "Chỉ tiêu KT-XH", "app.catalog.models.IndicatorPlan", "quan_tri|canh_bao", (
        F("indicator_id", "Chỉ tiêu", "ref", True, ref="indicator"), F("nam", "Năm", "int", True), F("ky", "Kỳ", "ky", True, help=KY_HELP),
        F("gia_tri_ke_hoach", "Giá trị kế hoạch", "dec", True), F("can_cu", "Căn cứ giao"),
    ), order=("indicator_id", "ky"), search=("ky", "can_cu"), link="/chi-tieu", defaults={"can_cu": ""},
        mo_ta="Kế hoạch được giao từng năm/kỳ do UBND phường lập (DT II.1); không nội suy mục tiêu 2030 (Phụ lục 01)."),
    Dataset("so_lieu", "Số liệu chỉ tiêu", "Chỉ tiêu KT-XH", "app.indicators.models.IndicatorValue", "@indicator", (
        F("indicator_id", "Chỉ tiêu", "ref", True, ref="indicator"), F("ky_bao_cao", "Kỳ báo cáo", "ky", True, help=KY_HELP),
        F("gia_tri", "Giá trị", "dec"), F("du_bao", "Dự báo/ước", "dec", list=False),
        F("nguon_loai", "Loại nguồn", "enum", True, {"phuong": "Phường", "chuyen_nganh": "Chuyên ngành", "api": "API"}),
        F("nguon", "Nguồn", required=True), F("don_vi_cung_cap", "Đơn vị cung cấp", required=True),
        F("thoi_diem_chot", "Thời điểm chốt", "datetime", True), F("trang_thai", "Trạng thái", "enum", options=TT_XN, readonly=True),
        F("nguoi_xac_nhan_ten", "Người xác nhận", readonly=True), F("ly_do", "Ghi chú/lý do", "textarea", list=False),
    ), order=("indicator_id", "ky_bao_cao"), search=("ky_bao_cao", "nguon", "don_vi_cung_cap"), link="/nhap-lieu",
        confirm=Confirm("trang_thai", ("da_xac_nhan", "tu_choi"), "tam_thoi", ("nguoi_xac_nhan_id", "nguoi_xac_nhan_ten", "ngay_xac_nhan")),
        mo_ta="Số mới hoặc số đã sửa ở trạng thái Tạm thời, phải được cán bộ xác nhận lại tại Nhập liệu & xác nhận.",
        defaults={"minh_chung_keys": [], "ly_do": "", "version": 1}),
    Dataset("nhiem_vu", "Nhiệm vụ, chương trình trọng tâm", "Chỉ tiêu KT-XH", "app.catalog.models.Program", "quan_tri|canh_bao", (
        F("ma", "Mã", required=True, create_only=True), F("ten", "Tên nhiệm vụ", required=True), F("mo_ta", "Mô tả", "textarea", list=False),
        F("don_vi_chu_tri", "Đơn vị chủ trì"),
        F("trang_thai", "Trạng thái", "enum", True, {"dang_thuc_hien": "Đang thực hiện", "hoan_thanh": "Hoàn thành", "tam_dung": "Tạm dừng", "chua_trien_khai": "Chưa triển khai"}),
    ), order=("ma",), search=("ma", "ten", "don_vi_chu_tri"), sample=False, link="/nhiem-vu", defaults={"mo_ta": "", "don_vi_chu_tri": "", "indicator_ids": []}),
    # ---------------- Ngân sách ----------------
    Dataset("ngan_sach", "Thu – chi ngân sách", "Ngân sách", "app.budget.models.BudgetLine", "ngan_sach", (
        F("nam", "Năm", "int", True), F("ky", "Kỳ", "ky", True, help=KY_HELP), F("loai", "Loại", "enum", True, {"thu": "Thu", "chi": "Chi"}),
        F("nhom_ma", "Nhóm thu/chi", "text", True, help="Mã nhóm thu (THUE_CTN, TIEN_SDD…) hoặc nhóm chi (CHI_DTPT, CHI_QLHC…)"),
        F("nhiem_vu", "Nhiệm vụ chi", "cat", cat="nhiem_vu_chi"),
        F("scope", "Phạm vi", "enum", True, {"dia_ban": "Thu trên địa bàn", "ns_phuong": "Ngân sách phường"}),
        F("du_toan", "Dự toán", "dec"), F("ke_hoach_ky", "Kế hoạch kỳ", "dec"), F("thuc_hien", "Thực hiện", "dec"), F("uoc_th", "Ước thực hiện", "dec", list=False),
        F("nguon_loai", "Nguồn", "enum", True, {"bao_cao_chot": "Báo cáo chốt", "api": "API"}), F("ngay_chot", "Ngày chốt", "datetime", list=False),
        F("trang_thai_doi_soat", "Đối soát", "enum", options={"cho_doi_soat": "Chờ đối soát", "da_doi_soat": "Đã đối soát"}, readonly=True),
    ), order=("nam", "ky", "loai", "nhom_ma"), search=("ky", "nhom_ma", "nhiem_vu"), link="/ngan-sach",
        confirm=Confirm("trang_thai_doi_soat", ("da_doi_soat",), "cho_doi_soat"),
        mo_ta="Kỳ đã đối soát: sửa sẽ chuyển về Chờ đối soát, phải chốt đối soát lại (có biên bản nếu chênh lệch). Đơn vị: đồng.",
        defaults={"trang_thai_doi_soat": "cho_doi_soat"}),
    # ---------------- Đầu tư công ----------------
    Dataset("du_an", "Dự án đầu tư công", "Đầu tư công", "app.projects.models.Project", "dau_tu_cong", (
        F("ma_du_an", "Mã dự án", required=True, create_only=True), F("ten", "Tên dự án", required=True),
        F("lop", "Lớp theo dõi", "enum", True, {"1": "1 – Phường làm chủ đầu tư", "2": "2 – Cấp thành phố làm chủ đầu tư", "3": "3 – Dự án khác (chỉ theo dõi)"}),
        F("chu_dau_tu", "Chủ đầu tư", required=True), F("nguon_von", "Nguồn vốn", "cat", True, cat="nguon_von"),
        F("tong_muc_dt", "Tổng mức đầu tư (đồng)", "dec"), F("dia_diem", "Địa điểm", list=False), F("lat", "Vĩ độ", "dec", list=False), F("lng", "Kinh độ", "dec", list=False),
        F("ngay_ht_ke_hoach", "Hoàn thành theo kế hoạch", "date"),
        F("trang_thai", "Trạng thái", "enum", True, {"dang_thuc_hien": "Đang thực hiện", "hoan_thanh": "Hoàn thành", "tam_dung": "Tạm dừng", "chuan_bi": "Chuẩn bị đầu tư"}),
        F("don_vi_phu_trach", "Đơn vị phụ trách"),
    ), order=("ma_du_an",), search=("ma_du_an", "ten", "chu_dau_tu"), link="/dau-tu-cong",
        mo_ta="Xóa dự án sẽ xóa kèm kế hoạch vốn, giải ngân, mốc tiến độ, vướng mắc của dự án.", defaults={"dia_diem": "", "don_vi_phu_trach": ""}),
    Dataset("ke_hoach_von", "Kế hoạch vốn", "Đầu tư công", "app.projects.models.CapitalPlan", "dau_tu_cong", (
        F("project_id", "Dự án", "ref", True, ref="project"), F("nam", "Năm", "int", True), F("ky", "Kỳ", "ky", True, help=KY_HELP),
        F("ke_hoach_von", "Kế hoạch vốn (đồng)", "dec", True),
    ), order=("project_id", "ky"), search=("ky",), link="/dau-tu-cong"),
    Dataset("giai_ngan", "Giải ngân", "Đầu tư công", "app.projects.models.Disbursement", "dau_tu_cong", (
        F("project_id", "Dự án", "ref", True, ref="project"), F("ky", "Kỳ", "ky", True, help=KY_HELP), F("luy_ke", "Lũy kế giải ngân (đồng)", "dec"),
        F("khoi_luong_pct", "Khối lượng (%)", "dec"), F("nguon", "Nguồn số liệu"),
        F("trang_thai_xac_nhan", "Xác nhận", "enum", options=TT_XN, readonly=True),
    ), order=("project_id", "ky"), search=("ky", "nguon"), link="/dau-tu-cong",
        confirm=Confirm("trang_thai_xac_nhan", ("da_xac_nhan",), "tam_thoi"), defaults={"nguon": "Chủ đầu tư báo cáo", "trang_thai_xac_nhan": "tam_thoi"}),
    Dataset("moc_tien_do", "Mốc tiến độ dự án", "Đầu tư công", "app.projects.models.Milestone", "dau_tu_cong", (
        F("project_id", "Dự án", "ref", True, ref="project"),
        F("loai", "Mốc", "enum", True, {"dau_thau": "Đấu thầu", "khoi_cong": "Khởi công", "thi_cong": "Thi công", "nghiem_thu": "Nghiệm thu", "ban_giao": "Bàn giao"}),
        F("han", "Hạn", "date", True), F("ngay_thuc_te", "Ngày thực tế", "date"),
    ), order=("project_id", "han"), link="/dau-tu-cong"),
    Dataset("vuong_mac", "Vướng mắc dự án", "Đầu tư công", "app.projects.models.ProjectIssue", "dau_tu_cong", (
        F("project_id", "Dự án", "ref", True, ref="project"), F("noi_dung", "Nội dung", "textarea", True), F("nguyen_nhan", "Nguyên nhân", "textarea", list=False),
        F("trach_nhiem", "Trách nhiệm"), F("huong_xu_ly", "Hướng xử lý", "textarea", list=False), F("can_quyet_dinh", "Cần lãnh đạo quyết định", "bool"),
        F("han", "Hạn", "date"), F("trang_thai", "Trạng thái", "enum", True, {"dang_xu_ly": "Đang xử lý", "da_xu_ly": "Đã xử lý"}),
    ), order=("project_id", "id"), search=("noi_dung", "trach_nhiem"), link="/dau-tu-cong",
        defaults={"nguyen_nhan": "", "trach_nhiem": "", "huong_xu_ly": "", "ho_so_keys": []}),
    # ---------------- Công trình ----------------
    Dataset("cong_trinh", "Công trình", "Công trình – đô thị", "app.works.models.Work", "cong_trinh", (
        F("ma_cong_trinh", "Mã công trình", required=True, create_only=True), F("ten", "Tên công trình", required=True),
        F("loai", "Loại", "cat", True, cat="loai_cong_trinh"), F("project_id", "Thuộc dự án", "ref", ref="project", list=False),
        F("dia_diem", "Địa điểm", list=False), F("lat", "Vĩ độ", "dec", list=False), F("lng", "Kinh độ", "dec", list=False),
        F("don_vi_thuc_hien", "Đơn vị thực hiện"), F("chu_dau_tu", "Chủ đầu tư", list=False), F("ngay_kc", "Khởi công", "date", list=False),
        F("ngay_ht", "Hoàn thành KH", "date"), F("chat_luong", "Chất lượng", "enum", options={"dat": "Đạt", "can_khac_phuc": "Cần khắc phục"}),
        F("camera_url", "Liên kết camera", list=False),
        F("trang_thai", "Trạng thái", "enum", True, {"dang_thi_cong": "Đang thi công", "hoan_thanh": "Hoàn thành", "tam_dung": "Tạm dừng"}),
    ), order=("ma_cong_trinh",), search=("ma_cong_trinh", "ten", "don_vi_thuc_hien"), link="/cong-trinh",
        mo_ta="Xóa công trình sẽ xóa kèm lịch sử cập nhật tiến độ.", defaults={"dia_diem": "", "don_vi_thuc_hien": "", "chu_dau_tu": ""}),
    Dataset("tien_do", "Cập nhật tiến độ công trình", "Công trình – đô thị", "app.works.models.WorkProgress", "cong_trinh", (
        F("work_id", "Công trình", "ref", True, ref="work"), F("ngay", "Ngày cập nhật", "date", True), F("ke_hoach_pct", "Kế hoạch (%)", "dec"),
        F("thuc_te_pct", "Thực tế (%)", "dec"), F("gpmb", "GPMB", "textarea", list=False), F("vuong_mac", "Vướng mắc", "textarea", list=False),
        F("can_quyet_dinh", "Cần quyết định", "bool"), F("trang_thai_xac_nhan", "Xác nhận", "enum", options=TT_XN, readonly=True),
    ), order=("work_id", "ngay"), search=("vuong_mac", "gpmb"), link="/cong-trinh",
        confirm=Confirm("trang_thai_xac_nhan", ("da_xac_nhan",), "tam_thoi", ("nguoi_xac_nhan_id",)),
        defaults={"gpmb": "", "vuong_mac": "", "anh_keys": [], "minh_chung_keys": [], "trang_thai_xac_nhan": "tam_thoi"}),
    # ---------------- Dân cư ----------------
    Dataset("dan_cu", "Thống kê dân cư tổng hợp", "Dân cư – an sinh", "app.population.models.PopulationStat", "dan_cu", (
        F("ky", "Kỳ", "ky", True, help=KY_HELP), F("tdp_id", "Tổ dân phố/thôn", "ref", ref="tdp"),
        F("chi_so", "Chỉ số", "enum", True, {"nhan_khau": "Nhân khẩu", "so_ho": "Số hộ", "sinh": "Sinh", "tu": "Tử", "chuyen_den": "Chuyển đến", "chuyen_di": "Chuyển đi",
                                             "ho_ngheo": "Hộ nghèo", "bhyt": "Người tham gia BHYT"}),
        F("gioi", "Giới", "enum", options={"": "Chung", "nam": "Nam", "nu": "Nữ"}), F("nhom_tuoi", "Nhóm tuổi", help="VD 0-4, 5-9 … 85+; để trống nếu không chia"),
        F("gia_tri", "Giá trị", "dec", True),
    ), order=("ky", "chi_so", "tdp_id"), search=("ky", "chi_so", "nhom_tuoi"), link="/dan-cu",
        mo_ta="Chỉ số liệu tổng hợp, không có thông tin cá nhân (DT I.3).", defaults={"gioi": "", "nhom_tuoi": ""}),
    # ---------------- TTHC – PAKN ----------------
    Dataset("tthc", "Hồ sơ TTHC theo ngày", "Dịch vụ công – PAKN", "app.services_pakn.models.AdminServiceStat", "tthc_pakn", (
        F("ngay", "Ngày", "date", True), F("bo_phan", "Bộ phận", required=True), F("linh_vuc", "Lĩnh vực", "cat", True, cat="linh_vuc_tthc"),
        F("tiep_nhan", "Tiếp nhận", "int", True), F("giai_quyet", "Giải quyết", "int", True), F("dung_han", "Đúng hạn", "int", True),
        F("qua_han", "Quá hạn", "int", True), F("truc_tuyen", "Trực tuyến", "int", True),
        F("nguon", "Nguồn", "enum", True, {"bieu_mau": "Biểu mẫu", "api": "API"}), F("trang_thai", "Trạng thái", "enum", options=TT_XN, readonly=True),
    ), order=("ngay", "bo_phan"), search=("bo_phan", "linh_vuc"), link="/hanh-chinh",
        confirm=Confirm("trang_thai", ("da_xac_nhan",), "tam_thoi"), defaults={"trang_thai": "tam_thoi"}),
    Dataset("pakn", "Phản ánh kiến nghị", "Dịch vụ công – PAKN", "app.services_pakn.models.FeedbackTicket", "tthc_pakn", (
        F("ma", "Mã", required=True, create_only=True), F("loai_viec", "Loại việc", "cat", True, cat="loai_pakn"), F("linh_vuc", "Lĩnh vực", "cat", True, cat="loai_pakn"),
        F("tdp_id", "Tổ dân phố/thôn", "ref", ref="tdp"), F("ngay_nhan", "Ngày nhận", "date", True), F("han_xu_ly", "Hạn xử lý", "date", True),
        F("so_ngay_quy_dinh", "Số ngày quy định", "int", True), F("ngay_hoan_thanh", "Ngày hoàn thành", "date"),
        F("trang_thai", "Trạng thái", "enum", True, {"tiep_nhan": "Tiếp nhận", "dang_xu_ly": "Đang xử lý", "qua_han": "Quá hạn", "hoan_thanh": "Hoàn thành"}),
        F("trang_thai_tra_loi", "Trả lời", "enum", True, {"chua_tra_loi": "Chưa trả lời", "da_tra_loi": "Đã trả lời"}),
        F("danh_gia_hai_long", "Hài lòng (1–5)", "int"),
    ), order=("ngay_nhan",), search=("ma", "loai_viec"), link="/hanh-chinh"),
    Dataset("phan_anh", "Phản ánh hiện trường", "Dịch vụ công – PAKN", "app.field_reports.models.FieldReport", "tthc_pakn", (
        F("ma", "Mã", readonly=True), F("tieu_de", "Tiêu đề", required=True), F("mo_ta", "Mô tả", "textarea", list=False),
        F("linh_vuc", "Lĩnh vực", required=True), F("khan_cap", "Khẩn cấp", "bool"), F("tdp_id", "Tổ dân phố/thôn", "ref", ref="tdp"),
        F("dia_chi", "Địa chỉ"), F("han_xu_ly", "Hạn xử lý", "date"), F("trang_thai", "Trạng thái", "text", readonly=True),
    ), order=("tiep_nhan_luc",), search=("ma", "tieu_de", "dia_chi"), link="/phan-anh",
        mo_ta="Sửa nội dung mô tả, địa bàn. Giao việc, tiến độ, xác nhận hoàn thành thực hiện tại màn hình Phản ánh hiện trường (để có lịch sử xử lý). "
              "Thêm mới tại màn hình Phản ánh hiện trường.", them=False, them_link="/phan-anh?tiep_nhan=1"),
    # ---------------- GD – YT – MT ----------------
    Dataset("diem", "Điểm trường, y tế, môi trường", "Giáo dục – Y tế – Môi trường", "app.quality_of_life.models.PointOfInterest", "gd_yt_mt", (
        F("loai", "Loại", "enum", True, {"truong": "Trường học", "tram_y_te": "Trạm y tế", "diem_moi_truong": "Điểm môi trường"}),
        F("ten", "Tên", required=True), F("lat", "Vĩ độ", "dec", True), F("lng", "Kinh độ", "dec", True),
        F("chat_luong_du_lieu", "Chất lượng dữ liệu", "enum", True, {"dat": "Đạt", "chua_dat": "Chưa đạt"}),
        F("cho_phep_hien_thi", "Được phép hiển thị", "bool"),
    ), order=("loai", "ten"), search=("ten",), link="/chat-luong-song",
        mo_ta="Chỉ điểm đạt chất lượng và được phép mới hiện trên bản đồ (DT II.7).", defaults={"thuoc_tinh": {}, "cho_phep_hien_thi": True}),
    # ---------------- Điều hành ----------------
    Dataset("thong_bao", "Thông báo điều hành", "Điều hành", "app.thong_bao.models.ThongBao", "quan_tri|canh_bao", (
        F("tieu_de", "Tiêu đề", required=True), F("noi_dung", "Nội dung", "textarea", list=False),
        F("lien_ket", "Liên kết", help="Đường dẫn trong hệ thống (VD /canh-bao) hoặc bài trên Cổng TTĐT (https://…)", list=False),
        F("muc_do", "Mức độ", "enum", True, {"thuong": "Thông thường", "quan_trong": "Quan trọng", "khan": "Khẩn"}),
        F("tu_ngay", "Hiệu lực từ", "date", True), F("den_ngay", "Đến ngày", "date"),
        F("doi_tuong", "Gửi tới (để trống = mọi người)", "multi", options={"lanh_dao": "Lãnh đạo", "xac_nhan": "Cán bộ xác nhận", "nhap_lieu": "Cán bộ nhập liệu",
                                                                       "chuyen_nganh": "Cơ quan chuyên ngành", "quan_tri_don_vi": "Quản trị đơn vị",
                                                                       "nguoi_xem": "Người xem", "man_hinh_tv": "Màn hình TV"}),
        F("ghim", "Ghim lên đầu", "bool"), F("hien_tren_tv", "Hiện trên màn hình TV", "bool"),
    ), order=("tu_ngay",), search=("tieu_de", "noi_dung"), link="/",
        mo_ta="Hiện trên dải bản tin dưới đầu trang trong thời gian hiệu lực. Thông báo khẩn và ghim chạy trước.",
        defaults={"noi_dung": "", "doi_tuong": [], "hien_tren_tv": True}),
    Dataset("lich_cong_tac", "Lịch công tác", "Điều hành", "app.lich.models.LichCongTac", "quan_tri|canh_bao", (
        F("ngay", "Ngày", "date", True), F("gio_bat_dau", "Bắt đầu", "time", True), F("gio_ket_thuc", "Kết thúc", "time"),
        F("noi_dung", "Nội dung", "textarea", True), F("chu_tri", "Chủ trì"), F("dia_diem", "Địa điểm"),
        F("thanh_phan", "Thành phần", "textarea", list=False), F("don_vi_chuan_bi", "Đơn vị chuẩn bị", list=False),
        F("loai", "Loại", "enum", True, {"hop": "Họp", "lam_viec": "Làm việc", "tiep_dan": "Tiếp công dân", "kiem_tra": "Kiểm tra", "cong_tac": "Công tác", "khac": "Khác"}),
        F("trang_thai", "Trạng thái", "enum", True, {"chinh_thuc": "Chính thức", "du_kien": "Dự kiến", "hoan": "Hoãn"}),
        F("hien_tren_tv", "Hiện trên màn hình TV", "bool", list=False), F("ghi_chu", "Ghi chú", "textarea", list=False),
    ), order=("ngay", "gio_bat_dau"), search=("noi_dung", "chu_tri", "dia_diem"), link="/lich-cong-tac",
        mo_ta="Lịch công tác tuần của lãnh đạo; hiện trên trang chủ (lịch hôm nay) và màn hình TV.",
        defaults={"chu_tri": "", "dia_diem": "", "thanh_phan": "", "don_vi_chuan_bi": "", "ghi_chu": "", "hien_tren_tv": True}),
    Dataset("van_ban", "Văn bản chỉ đạo điều hành", "Điều hành", "app.van_ban.models.VanBan", "quan_tri|canh_bao", (
        F("so_ky_hieu", "Số, ký hiệu", required=True), F("ngay_ban_hanh", "Ngày ban hành", "date", True),
        F("loai", "Loại văn bản", "enum", True, {"nghi_quyet": "Nghị quyết", "quyet_dinh": "Quyết định", "chi_thi": "Chỉ thị", "ke_hoach": "Kế hoạch",
                                                "thong_bao": "Thông báo kết luận", "cong_van": "Công văn", "bao_cao": "Báo cáo"}),
        F("co_quan_ban_hanh", "Cơ quan ban hành", required=True), F("nguoi_ky", "Người ký", list=False), F("trich_yeu", "Trích yếu", "textarea", True),
        F("file_key", "Tệp văn bản (PDF/Word)", "file", list=False), F("lien_ket", "Liên kết", list=False, help="Bài đăng trên Cổng TTĐT hoặc hệ thống văn bản (https://…)"),
        F("han_thuc_hien", "Hạn thực hiện", "date"), F("trang_thai", "Hiệu lực", "enum", True, {"con_hieu_luc": "Còn hiệu lực", "het_hieu_luc": "Hết hiệu lực"}),
        F("nhiem_vu_ids", "Nhiệm vụ chỉ đạo theo văn bản", "refmulti", ref="case", list=False),
    ), order=("ngay_ban_hanh",), search=("so_ky_hieu", "trich_yeu", "co_quan_ban_hanh"), link="/van-ban",
        mo_ta="Gắn văn bản với nhiệm vụ chỉ đạo để theo dõi tiến độ thực hiện theo từng văn bản.", defaults={"nguoi_ky": "", "nhiem_vu_ids": []}),
    # ---------------- Danh mục ----------------
    Dataset("dia_ban", "Thôn, tổ dân phố", "Danh mục", "app.platform.models.ResidentialGroup", "quan_tri", (
        F("ma_tdp", "Mã", required=True), F("ten", "Tên", required=True), F("loai", "Loại", "enum", options={"tdp": "Tổ dân phố", "thon": "Thôn"}),
        F("nguoi_dung_dau", "Người đứng đầu"), F("dien_thoai", "Điện thoại"), F("lat", "Vĩ độ", "dec", list=False), F("lng", "Kinh độ", "dec", list=False),
        F("ngung_hoat_dong", "Ngừng hoạt động", "bool"),
    ), order=("ma_tdp",), search=("ma_tdp", "ten", "nguoi_dung_dau"), sample=False, link="/quan-tri?tab=danh-muc"),
    Dataset("anh_xa_dvhc", "Ánh xạ đơn vị trước sắp xếp", "Danh mục", "app.platform.models.AdminUnitMapping", "quan_tri", (
        F("ma_cu", "Mã đơn vị cũ", required=True), F("ten_cu", "Tên đơn vị cũ", required=True), F("hieu_luc_den", "Hiệu lực đến", "date"),
    ), order=("ma_cu",), search=("ma_cu", "ten_cu"), sample=False, mo_ta="Bảng ánh xạ 04 đơn vị trước sắp xếp để so sánh số liệu quá khứ (DT III.2)."),
    Dataset("can_bo", "Cán bộ, công chức", "Danh mục", "app.org.models.Staff", "quan_tri", (
        F("ma", "Mã", required=True, create_only=True), F("don_vi_ma", "Mã đơn vị", required=True), F("ho_ten", "Họ tên", required=True),
        F("chuc_vu", "Chức vụ", required=True), F("cap", "Cấp", "enum", True, {"truong": "Người đứng đầu", "pho": "Cấp phó", "thanh_vien": "Thành viên"}),
        F("dien_thoai", "Điện thoại"), F("email", "Email", list=False), F("nhiem_vu", "Nhiệm vụ phụ trách", "textarea", list=False),
    ), order=("don_vi_ma", "thu_tu"), search=("ho_ten", "chuc_vu", "don_vi_ma"), link="/co-cau-to-chuc?tab=danh-ba",
        defaults={"nhiem_vu": "", "linh_vuc": [], "dia_ban_ids": [], "thu_tu": 99}),
]
BY_KEY = {d.key: d for d in DATASETS}
