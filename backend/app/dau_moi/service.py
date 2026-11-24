"""Danh mục đầu mối mặc định theo dự thảo kịch bản (DT II "Nguồn và trách nhiệm", V.1, Phụ lục 01, 02) và tra cứu
đầu mối chịu trách nhiệm cho từng chỉ tiêu, nguồn dữ liệu, nhóm dữ liệu."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dau_moi.models import DauMoi

VAI_TRO = {"chu_tri": "Chủ trì", "phoi_hop": "Phối hợp", "cung_cap": "Cung cấp số liệu", "xac_nhan": "Xác nhận"}
NHOM_TN = ["chung", "ktxh", "dan_cu", "ngan_sach", "dau_tu_cong", "cong_trinh", "tthc_pakn", "gd_yt_mt"]
CAP = {"phuong": "Phường", "thanh_pho": "Thành phố", "chuyen_nganh": "Cơ quan chuyên ngành", "chu_dau_tu": "Chủ đầu tư"}
PHIEU = {
    "A": "Chỉ tiêu phát triển KT-XH", "B": "Thu, chi ngân sách", "C": "Danh mục đầu tư công", "D": "Tiến độ công trình",
    "E": "Đô thị, môi trường", "F": "An sinh, giáo dục, y tế", "G": "Hành chính, PAKN", "H": "Tài khoản người dùng",
}

# Phụ lục 02 — thông tin tối thiểu từng phiếu
PHIEU_TOI_THIEU = {
    "A": "Mã chỉ tiêu; mục tiêu năm; kết quả kỳ; dự báo; đơn vị đo; chứng từ/biểu mẫu nguồn",
    "B": "Dự toán; thực hiện theo nhóm thu/chi; kỳ chốt; phân biệt thu địa bàn và ngân sách phường",
    "C": "Mã dự án; chủ đầu tư; nguồn; kế hoạch vốn; giải ngân; khối lượng; hạn; vướng mắc",
    "D": "Mã công trình; địa điểm; ngày bắt đầu/kết thúc; tiến độ; hình ảnh; nguyên nhân chậm",
    "E": "Quy hoạch, đường giao thông, chiếu sáng, cấp nước, rác thải, nước thải",
    "F": "Hộ nghèo, BHYT, trường chuẩn, số liệu tổng hợp",
    "G": "Báo cáo hồ sơ TTHC, trạng thái phản ánh và thời hạn xử lý",
    "H": "Họ tên, đơn vị, chức danh, phạm vi khai thác và người phê duyệt",
}
# DT III.1 — mỗi đầu mối gửi tối thiểu
TOI_THIEU_CHUNG = ("Mã chỉ tiêu/dự án, định nghĩa và công thức tính, phạm vi địa bàn, năm/kỳ báo cáo, kế hoạch, thực hiện, đơn vị đo, "
                   "nguồn dữ liệu, thời điểm chốt, người xác nhận, kỳ cập nhật, định dạng và phân loại thông tin. Đối với dự án, bổ sung mã dự án, "
                   "chủ đầu tư, địa điểm, kế hoạch vốn, khối lượng, giải ngân và tình trạng vướng mắc.")


def _tn(*items: tuple[str, str, str]) -> list[dict]:
    return [{"nhom": n, "vai_tro": v, "noi_dung": c} for n, v, c in items]


def defaults(ten_dv: str) -> list[dict]:
    """`ten_dv`: tên đơn vị, VD 'Phường Việt Yên'. Nội dung trách nhiệm theo dự thảo, áp dụng chung cho xã/phường."""
    ubnd = f"UBND {ten_dv[0].lower() + ten_dv[1:]}"
    return [
        dict(ma="UBND", ten=ubnd, cap="phuong",
             noi_dung="Chủ trì xác định yêu cầu điều hành; ban hành/đề xuất bộ chỉ tiêu, phân công cán bộ cập nhật; rà soát, xác nhận "
                      "các nguồn thuộc phường và dùng hệ thống trong các cuộc họp.",
             trach_nhiem=_tn(("chung", "chu_tri", "Xác định yêu cầu điều hành, phân công cán bộ cập nhật, sử dụng trong giao ban"),
                             ("ktxh", "chu_tri", "Lập bảng chỉ tiêu, chỉ tiêu hằng năm và xác nhận"),
                             ("ngan_sach", "xac_nhan", "Bộ phận tài chính – kế toán rà soát, xác nhận đúng phạm vi ngân sách phường"),
                             ("dau_tu_cong", "phoi_hop", "Đối soát giải ngân cùng Sở Tài chính, Kho bạc, chủ đầu tư"),
                             ("cong_trinh", "cung_cap", "Bộ phận chuyên môn cập nhật tiến độ, vướng mắc, hình ảnh hiện trường"),
                             ("gd_yt_mt", "xac_nhan", "Xác nhận phạm vi số liệu cùng đơn vị chuyên ngành"),
                             ("dan_cu", "phoi_hop", "Chỉ khai thác số liệu dân cư tổng hợp được phép chia sẻ")),
             phieu_nguon=["A", "B", "C", "F", "H"],
             chi_tieu=["NQ01-13a", "NQ01-13b", "NQ01-13c", "NQ01-15"]),
        dict(ma="VPDU", ten="Văn phòng Đảng ủy phường", cap="phuong",
             noi_dung="Cung cấp số liệu công tác Đảng, đánh giá xếp loại tổ chức theo Nghị quyết 01-NQ/ĐU.",
             trach_nhiem=_tn(("ktxh", "cung_cap", "Chỉ tiêu 01–04 Nghị quyết 01-NQ/ĐU (công tác Đảng, tổ chức)")),
             phieu_nguon=["A"], chi_tieu=["NQ01-01a", "NQ01-01b", "NQ01-02", "NQ01-03a", "NQ01-03b", "NQ01-04"]),
        dict(ma="HCC", ten="Trung tâm Phục vụ hành chính công phường", cap="phuong",
             noi_dung="Nhập số liệu TTHC qua biểu mẫu động trong thời gian luồng Cổng DVCQG gián đoạn; theo dõi phản ánh kiến nghị.",
             trach_nhiem=_tn(("tthc_pakn", "cung_cap", "Hồ sơ TTHC tiếp nhận, giải quyết, đúng hạn/quá hạn, trực tuyến; trạng thái phản ánh")),
             phieu_nguon=["G"]),
        dict(ma="SOKHCN", ten="Sở Khoa học và Công nghệ", cap="thanh_pho",
             noi_dung="Chủ trì phương án kỹ thuật trên IOC thành phố, phân quyền, thiết kế dashboard, hỗ trợ chuẩn hóa/tích hợp và tổng hợp "
                      "kết quả thí điểm. Cấu hình tiếp nhận dữ liệu, nhật ký, kiểm thử, backup, giám sát và hỗ trợ kỹ thuật.",
             trach_nhiem=_tn(("chung", "chu_tri", "Phương án kỹ thuật, phân quyền, dashboard, tích hợp, nhật ký, sao lưu, giám sát")),
             phieu_nguon=["H"]),
        dict(ma="VPUBNDTP", ten="Văn phòng UBND thành phố", cap="thanh_pho",
             noi_dung="Phối hợp điều phối các nguồn dùng chung, đặc biệt giải quyết thủ tục hành chính và báo cáo phục vụ chỉ đạo điều hành.",
             trach_nhiem=_tn(("chung", "phoi_hop", "Điều phối nguồn dùng chung, báo cáo phục vụ chỉ đạo điều hành"),
                             ("tthc_pakn", "phoi_hop", "Luồng dữ liệu TTHC từ Cổng DVCQG")),
             phieu_nguon=["G"], nguon=["DVCQG_TTHC"]),
        dict(ma="STC", ten="Sở Tài chính", cap="chuyen_nganh",
             noi_dung="Xác nhận phạm vi và số liệu ngân sách, đầu tư công, giải ngân và phương thức chia sẻ. Chủ trì thống nhất biểu mẫu "
                      "và số liệu đối soát với nguồn Bộ Tài chính/Kho bạc.",
             trach_nhiem=_tn(("ngan_sach", "chu_tri", "Thống nhất biểu mẫu, đối soát số liệu theo kỳ chốt"),
                             ("dau_tu_cong", "xac_nhan", "Xác nhận kế hoạch vốn, giải ngân"), ("ktxh", "xac_nhan", "Xác nhận chỉ tiêu thu ngân sách")),
             phieu_nguon=["B", "C"], chi_tieu=["NQ01-05a", "NQ01-05b"]),
        dict(ma="KBNN", ten="Kho bạc Nhà nước", cap="chuyen_nganh",
             noi_dung="Cung cấp, đối soát số liệu thu, chi và giải ngân vốn đầu tư công.",
             trach_nhiem=_tn(("ngan_sach", "cung_cap", "Số liệu thu, chi qua Kho bạc"), ("dau_tu_cong", "cung_cap", "Số giải ngân theo dự án")),
             phieu_nguon=["B", "C"]),
        dict(ma="THUE", ten="Cơ quan Thuế", cap="chuyen_nganh",
             noi_dung="Cung cấp số thu ngân sách nhà nước trên địa bàn theo nhóm khoản thu.",
             trach_nhiem=_tn(("ngan_sach", "cung_cap", "Số thu NSNN trên địa bàn"), ("ktxh", "cung_cap", "Tổng thu, thu nội địa")),
             phieu_nguon=["B"], chi_tieu=["NQ01-05a", "NQ01-05b"]),
        dict(ma="CATP", ten="Công an thành phố và cơ quan quản lý nguồn dân cư", cap="chuyen_nganh",
             noi_dung="Xác định dữ liệu thống kê dân cư nào được phép chia sẻ tới cấp phường; đối soát phạm vi, kỳ dữ liệu và an toàn thông tin.",
             trach_nhiem=_tn(("dan_cu", "cung_cap", "Thống kê dân cư tổng hợp qua Kho dữ liệu dùng chung (C12)"),
                             ("dan_cu", "xac_nhan", "Phạm vi được phép chia sẻ, kỳ dữ liệu, an toàn thông tin")),
             phieu_nguon=["F"], nguon=["KHO_DL_DAN_CU"]),
        dict(ma="SXD", ten="Sở Xây dựng", cap="chuyen_nganh",
             noi_dung="Cung cấp, xác nhận danh mục, các mốc tiến độ công trình, dữ liệu đô thị, quy hoạch, hạ tầng theo phạm vi quản lý.",
             trach_nhiem=_tn(("cong_trinh", "xac_nhan", "Danh mục, mốc tiến độ công trình; chỉ tiêu quy hoạch, hạ tầng")),
             phieu_nguon=["D", "E"], chi_tieu=["NQ01-07a", "NQ01-07b", "NQ01-08a", "NQ01-08b", "DT-CX"]),
        dict(ma="BQLDA", ten="Ban QLDA và chủ đầu tư", cap="chu_dau_tu",
             noi_dung="Xác nhận giải ngân, khối lượng, tiến độ và vướng mắc của dự án, công trình do mình quản lý; có minh chứng.",
             trach_nhiem=_tn(("dau_tu_cong", "xac_nhan", "Giải ngân và tiến độ dự án"), ("cong_trinh", "xac_nhan", "Tiến độ, minh chứng hiện trường")),
             phieu_nguon=["C", "D"]),
        dict(ma="SGDDT", ten="Sở Giáo dục và Đào tạo", cap="chuyen_nganh",
             noi_dung="Cung cấp, xác nhận số liệu trường lớp, học sinh, trường chuẩn quốc gia.",
             trach_nhiem=_tn(("gd_yt_mt", "cung_cap", "Trường lớp, học sinh, trường chuẩn quốc gia mức độ 2")),
             phieu_nguon=["F"], chi_tieu=["NQ01-11", "DT-TRUONG", "DT-LOP", "DT-HS"]),
        dict(ma="BHXH", ten="Bảo hiểm xã hội và Sở Y tế", cap="chuyen_nganh",
             noi_dung="Cung cấp tỷ lệ tham gia BHYT, số liệu y tế tổng hợp; không công khai hồ sơ sức khỏe cá nhân.",
             trach_nhiem=_tn(("gd_yt_mt", "cung_cap", "Tỷ lệ dân số tham gia BHYT, y tế tổng hợp")),
             phieu_nguon=["F"], chi_tieu=["NQ01-12"]),
        dict(ma="MTCN", ten="Đơn vị cấp nước, thu gom rác và môi trường", cap="chuyen_nganh",
             noi_dung="Cung cấp, xác nhận số liệu nước sạch, thu gom – xử lý rác thải, nước thải đô thị.",
             trach_nhiem=_tn(("gd_yt_mt", "cung_cap", "Nước sạch, rác thải, nước thải")),
             phieu_nguon=["E"], chi_tieu=["NQ01-14", "NQ01-15", "NQ01-16"]),
        dict(ma="THONGKE", ten="Cơ quan thống kê", cap="chuyen_nganh",
             noi_dung="Cung cấp số liệu thống kê, điều tra đã thẩm định (giá trị sản phẩm, thu nhập bình quân).",
             trach_nhiem=_tn(("ktxh", "cung_cap", "Giá trị sản phẩm, thu nhập bình quân")), phieu_nguon=["A"], chi_tieu=["NQ01-06", "NQ01-09"]),
        dict(ma="PAKN", ten="Cơ quan quản lý hệ thống phản ánh kiến nghị", cap="thanh_pho",
             noi_dung="Vận hành API phản ánh kiến nghị về IOC thành phố; thời hạn xử lý theo quy định từng loại việc.",
             trach_nhiem=_tn(("tthc_pakn", "cung_cap", "Phản ánh kiến nghị qua API")), phieu_nguon=["G"], nguon=["PAKN_API"]),
    ]


async def ensure(s: AsyncSession, tenant_id: int, ten_dv: str) -> list[DauMoi]:
    rows = list((await s.execute(select(DauMoi).where(DauMoi.tenant_id == tenant_id).order_by(DauMoi.thu_tu, DauMoi.id))).scalars())
    if rows:
        return rows
    rows = [DauMoi(tenant_id=tenant_id, thu_tu=i, **d) for i, d in enumerate(defaults(ten_dv))]
    s.add_all(rows)
    await s.flush()
    return rows


class Lookup:
    """Tra đầu mối chịu trách nhiệm: chỉ tiêu (theo danh sách chỉ tiêu, ưu tiên vai trò cung cấp), nguồn, nhóm."""

    def __init__(self, rows: list[DauMoi]):
        self.rows = rows

    def _rank(self, d: DauMoi) -> int:
        roles = {t["vai_tro"] for t in d.trach_nhiem or []}
        return 0 if "cung_cap" in roles else (1 if "xac_nhan" in roles else 2)

    def chi_tieu(self, ma: str, nhom: str | None = None) -> list[DauMoi]:
        hit = sorted([d for d in self.rows if ma in (d.chi_tieu or [])], key=self._rank)
        return hit if hit or not nhom else self.nhom(nhom, ("cung_cap",))

    def nguon(self, ma: str) -> list[DauMoi]:
        return [d for d in self.rows if ma in (d.nguon or [])]

    def nhom(self, nhom: str | None, vai_tro: tuple[str, ...] = ("chu_tri", "phoi_hop", "cung_cap", "xac_nhan")) -> list[DauMoi]:
        return [d for d in self.rows if any(t["nhom"] == nhom and t["vai_tro"] in vai_tro for t in d.trach_nhiem or [])]

    def cua_user(self, uid: int) -> list[DauMoi]:
        return [d for d in self.rows if uid in (d.user_ids or [])]


def brief(rows: list[DauMoi]) -> list[dict]:
    return [{"ma": d.ma, "ten": d.ten} for d in rows]


async def lookup(s: AsyncSession, tenant_id: int) -> Lookup:
    from app.platform.models import Tenant

    rows = list((await s.execute(select(DauMoi).where(DauMoi.tenant_id == tenant_id).order_by(DauMoi.thu_tu, DauMoi.id))).scalars())
    if not rows:  # chưa khởi tạo: dùng danh mục mặc định để tra (không ghi trong request chỉ đọc)
        t = await s.get(Tenant, tenant_id)
        rows = [DauMoi(tenant_id=tenant_id, thu_tu=i, user_ids=[], **d) for i, d in enumerate(defaults(t.ten if t else "đơn vị"))]
    return Lookup(rows)
