"""Đặc tả biểu mẫu nhập liệu (Phụ lục 02). Một đặc tả dùng chung cho: tệp Excel mẫu, đọc CSV, và biểu mẫu động trên giao diện."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.budget.models import BudgetLine
from app.catalog.models import Indicator
from app.core.formatting import parse_vn_date, parse_vn_number
from app.core.periods import parse_ky
from app.core.principal import CurrentUser
from app.indicators.models import IndicatorValue
from app.indicators.service import create_value
from app.projects.models import Disbursement, Project
from app.services_pakn.models import AdminServiceStat


@dataclass
class Col:
    ten: str
    kieu: str = "chu"  # chu | so | ngay | ky | lua_chon
    bat_buoc: bool = False
    lua_chon: list[str] = field(default_factory=list)
    goi_y: str = ""


@dataclass
class Spec:
    loai: str
    ten: str
    nhom: str
    cot: list[Col]
    huong_dan: list[str]


SPECS: dict[str, Spec] = {
    "chi_tieu": Spec("chi_tieu", "Số liệu chỉ tiêu kinh tế – xã hội", "*", [
        Col("Mã chỉ tiêu", "chu", True, goi_y="Chọn trong sheet Danh mục"), Col("Kỳ báo cáo", "ky", True, goi_y="2026-10 / 2026-Q3 / 2026"),
        Col("Giá trị", "so", goi_y="Để trống nếu chưa có số; không ghi 0"), Col("Dự báo/ước", "so"), Col("Nguồn", "chu", True),
        Col("Đơn vị cung cấp", "chu", True), Col("Thời điểm chốt", "ngay", True, goi_y="dd/mm/yyyy"),
        Col("Loại nguồn", "lua_chon", lua_chon=["phuong", "chuyen_nganh"], goi_y="phuong hoặc chuyen_nganh"), Col("Ghi chú/Lý do", "chu")],
        ["Mỗi dòng là số liệu của một chỉ tiêu trong một kỳ.", "Ô trống nghĩa là CHƯA CÓ SỐ — hệ thống không tự điền 0.",
         "Số thập phân dùng dấu phẩy (12,5) hoặc dấu chấm đều được.", "Số liệu nhập vào ở trạng thái Tạm thời, chờ cán bộ có thẩm quyền xác nhận.",
         "Sửa số đã xác nhận phải ghi lý do ở cột Ghi chú/Lý do."]),
    "ngan_sach": Spec("ngan_sach", "Số liệu thu, chi ngân sách", "ngan_sach", [
        Col("Kỳ", "ky", True, goi_y="2026-10 (lũy kế đến hết tháng)"), Col("Loại", "lua_chon", True, ["thu", "chi"]), Col("Mã nhóm", "chu", True),
        Col("Mã nhiệm vụ", "chu"), Col("Phạm vi", "lua_chon", True, ["dia_ban", "ns_phuong"], "dia_ban = thu trên địa bàn; ns_phuong = ngân sách phường"),
        Col("Dự toán", "so"), Col("Kế hoạch kỳ", "so"), Col("Thực hiện lũy kế", "so"), Col("Ước thực hiện", "so"),
        Col("Nguồn", "lua_chon", True, ["bao_cao_chot", "api"]), Col("Ngày chốt", "ngay", True)],
        ["Đơn vị: đồng.", "Thu trên địa bàn và thu ngân sách phường được hưởng ghi thành hai dòng riêng, không cộng gộp.",
         "Số liệu nhập vào ở trạng thái Chờ đối soát."]),
    "tthc": Spec("tthc", "Hồ sơ thủ tục hành chính (thay luồng Cổng DVCQG gián đoạn)", "tthc_pakn", [
        Col("Ngày", "ngay", True), Col("Bộ phận", "chu", True), Col("Lĩnh vực", "chu"), Col("Tiếp nhận", "so", True), Col("Giải quyết", "so", True),
        Col("Đúng hạn", "so", True), Col("Quá hạn", "so", True), Col("Trực tuyến", "so", True)],
        ["Mỗi dòng là số hồ sơ của một bộ phận trong một ngày.", "Số liệu nhập vào ở trạng thái Tạm thời."]),
    "giai_ngan": Spec("giai_ngan", "Giải ngân dự án đầu tư công", "dau_tu_cong", [
        Col("Mã dự án", "chu", True), Col("Kỳ", "ky", True), Col("Giải ngân lũy kế", "so", True), Col("Khối lượng (%)", "so")],
        ["Đơn vị: đồng. Giải ngân lũy kế từ đầu năm đến hết kỳ."]),
}


def parse_cell(col: Col, v: object) -> object:
    if col.kieu == "so":
        return parse_vn_number(v)
    if col.kieu == "ngay":
        return parse_vn_date(v)
    s = "" if v is None else str(v).strip()
    if col.kieu == "ky" and s:
        return str(parse_ky(s))
    if col.kieu == "lua_chon" and s and s not in col.lua_chon:
        raise ValueError(f"Chỉ nhận một trong: {', '.join(col.lua_chon)}")
    return s or None


def _int(v: Decimal | None) -> int:
    return int(v or 0)


async def validate_row(s: AsyncSession, user: CurrentUser, spec: Spec, row: dict, cache: dict) -> list[tuple[str, str]]:
    """Kiểm tra nghiệp vụ một dòng (đã parse). Trả về [(cột, thông báo)]."""
    err: list[tuple[str, str]] = []
    tid = s.info["tenant_id"]
    if spec.loai == "chi_tieu":
        if "inds" not in cache:
            cache["inds"] = {i.ma_chi_tieu: i for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tid))).scalars()}
        ind = cache["inds"].get(row["Mã chỉ tiêu"])
        if ind is None:
            err.append(("Mã chỉ tiêu", f"Mã chỉ tiêu {row['Mã chỉ tiêu']} không có trong danh mục"))
        elif not user.can("nhap", ind.nhom):
            err.append(("Mã chỉ tiêu", f"Bạn không có quyền nhập số liệu nhóm {ind.nhom}"))
        elif not row.get("Ghi chú/Lý do"):
            confirmed = (await s.execute(select(IndicatorValue.id).where(
                IndicatorValue.indicator_id == ind.id, IndicatorValue.ky_bao_cao == row["Kỳ báo cáo"],
                IndicatorValue.nguon_loai == (row.get("Loại nguồn") or "phuong"), IndicatorValue.trang_thai == "da_xac_nhan"))).first()
            if confirmed:
                err.append(("Ghi chú/Lý do", "Kỳ này đã có số được xác nhận, phải ghi lý do sửa"))
    elif spec.loai == "tthc":
        tn, gq, dh, qh, tt = (_int(row[k]) for k in ("Tiếp nhận", "Giải quyết", "Đúng hạn", "Quá hạn", "Trực tuyến"))
        if gq > tn:
            err.append(("Giải quyết", "Số đã giải quyết không được lớn hơn số tiếp nhận"))
        elif dh + qh > gq:
            err.append(("Quá hạn", "Số đúng hạn cộng quá hạn không được lớn hơn số đã giải quyết"))
        if tt > tn:
            err.append(("Trực tuyến", "Số hồ sơ trực tuyến không được lớn hơn số tiếp nhận"))
    elif spec.loai == "giai_ngan":
        if "projects" not in cache:
            cache["projects"] = {p.ma_du_an: p for p in (await s.execute(select(Project).where(Project.tenant_id == tid))).scalars()}
        if row["Mã dự án"] not in cache["projects"]:
            err.append(("Mã dự án", f"Mã dự án {row['Mã dự án']} không có trong danh mục"))
    elif spec.loai == "ngan_sach" and row.get("Loại") == "chi" and row.get("Phạm vi") == "dia_ban":
        err.append(("Phạm vi", "Số chi chỉ thuộc ngân sách phường (ns_phuong)"))
    return err


async def write_row(s: AsyncSession, user: CurrentUser, spec: Spec, row: dict, ten_tep: str, cache: dict) -> None:
    tid = s.info["tenant_id"]
    if spec.loai == "chi_tieu":
        ind = cache["inds"][row["Mã chỉ tiêu"]]
        chot = row["Thời điểm chốt"]
        await create_value(s, user, ind.id, {
            "ky_bao_cao": row["Kỳ báo cáo"], "gia_tri": row["Giá trị"], "du_bao": row["Dự báo/ước"], "nguon": row["Nguồn"],
            "don_vi_cung_cap": row["Đơn vị cung cấp"], "thoi_diem_chot": datetime(chot.year, chot.month, chot.day, tzinfo=UTC),
            "nguon_loai": row.get("Loại nguồn") or "phuong", "ly_do": row.get("Ghi chú/Lý do") or f"Nhập từ tệp {ten_tep}"})
    elif spec.loai == "tthc":
        s.add(AdminServiceStat(tenant_id=tid, ngay=row["Ngày"], bo_phan=row["Bộ phận"], linh_vuc=row.get("Lĩnh vực") or "",
                               **{k: _int(row[c]) for k, c in (("tiep_nhan", "Tiếp nhận"), ("giai_quyet", "Giải quyết"), ("dung_han", "Đúng hạn"),
                                                               ("qua_han", "Quá hạn"), ("truc_tuyen", "Trực tuyến"))},
                               nguon="bieu_mau", trang_thai="tam_thoi", nguoi_nhap_id=user.id))
    elif spec.loai == "giai_ngan":
        p = cache["projects"][row["Mã dự án"]]
        s.add(Disbursement(project_id=p.id, tenant_id=tid, ky=row["Kỳ"], luy_ke=row["Giải ngân lũy kế"], khoi_luong_pct=row["Khối lượng (%)"],
                           trang_thai_xac_nhan="tam_thoi", nguon=f"Nhập từ tệp {ten_tep}"))
    elif spec.loai == "ngan_sach":
        key = dict(tenant_id=tid, nam=int(row["Kỳ"][:4]), ky=row["Kỳ"], loai=row["Loại"], nhom_ma=row["Mã nhóm"], nhiem_vu=row.get("Mã nhiệm vụ"),
                   scope=row["Phạm vi"], nguon_loai=row["Nguồn"])
        q = select(BudgetLine).where(*[getattr(BudgetLine, k) == v if v is not None else getattr(BudgetLine, k).is_(None) for k, v in key.items()])
        b = (await s.execute(q)).scalar()
        if b is None:
            b = BudgetLine(**key)
            s.add(b)
        c = row["Ngày chốt"]
        b.du_toan, b.ke_hoach_ky, b.thuc_hien, b.uoc_th = row["Dự toán"], row["Kế hoạch kỳ"], row["Thực hiện lũy kế"], row["Ước thực hiện"]
        b.ngay_chot, b.trang_thai_doi_soat = datetime(c.year, c.month, c.day, tzinfo=UTC), "cho_doi_soat"
    else:
        raise HTTPException(422, "Loại biểu mẫu không hỗ trợ")
