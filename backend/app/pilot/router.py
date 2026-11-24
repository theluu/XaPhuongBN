"""Thí điểm và nghiệm thu (DT V.2 lộ trình 90 ngày, V.3 tiêu chí nghiệm thu, VI hồ sơ phường chuẩn bị).

Tiêu chí nghiệm thu tự tính từ dữ liệu thật của đơn vị — dữ liệu minh họa không bao giờ được tính là kết quả (DT V.3)."""
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, tenant_db
from app.core.db import admin_sessionmaker
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.platform.models import Tenant

router = APIRouter(prefix="/api/thi-diem", tags=["thi-diem"])

LOI = ["ktxh", "dan_cu", "ngan_sach", "dau_tu_cong", "cong_trinh"]  # dashboard lõi (DT V.2 ngày 16–45)
TEN_NHOM = {"ktxh": "Kinh tế – xã hội", "dan_cu": "Dân cư", "ngan_sach": "Ngân sách", "dau_tu_cong": "Đầu tư công", "cong_trinh": "Công trình",
            "tthc_pakn": "TTHC – phản ánh", "gd_yt_mt": "Giáo dục – y tế – môi trường"}

# DT V.2 — (mã, từ ngày, đến ngày, tên giai đoạn, [(mã việc, nội dung)])
LO_TRINH = [
    ("GD1", 1, 15, "Thống nhất phạm vi", [
        ("pham_vi", "Thống nhất phạm vi thí điểm"),
        ("chi_tieu", "Thống nhất bảng chỉ tiêu Nghị quyết 01-NQ/ĐU"),
        ("ma_dinh_danh", "Thống nhất mã định danh (đơn vị hành chính, chỉ tiêu, dự án, tổ dân phố)"),
        ("du_an", "Thống nhất danh sách dự án"),
        ("nguon_nguoi", "Thống nhất nguồn và người chịu trách nhiệm"),
        ("quyen_chia_se", "Kiểm tra quyền chia sẻ từng nguồn"),
    ]),
    ("GD2", 16, 45, "Dữ liệu mẫu và dashboard lõi", [
        ("chuan_hoa", "Chuẩn hóa bộ dữ liệu mẫu"),
        ("dashboard_loi", "Thiết lập dashboard lõi: KT-XH, dân cư, ngân sách, đầu tư công, công trình"),
        ("tich_hop", "Tích hợp các nguồn được cho phép"),
    ]),
    ("GD3", 46, 75, "Mở rộng và khai thác thử nghiệm", [
        ("mo_rong", "Mở rộng TTHC/phản ánh, an sinh – môi trường khi đủ điều kiện"),
        ("hai_ky", "Tổ chức 02 kỳ cập nhật"),
        ("khai_thac", "Tổ chức các phiên khai thác thử nghiệm"),
        ("hieu_chinh", "Hiệu chỉnh cảnh báo"),
    ]),
    ("GD4", 76, 90, "Đối soát, nghiệm thu", [
        ("doi_soat", "Đối soát số liệu"),
        ("nghiem_thu", "Nghiệm thu thử nghiệm"),
        ("muc_do_su_dung", "Đánh giá mức độ sử dụng"),
        ("bao_cao", "Lập báo cáo kiến nghị mở rộng, hoàn thiện"),
    ]),
]
# DT VI — hồ sơ UBND phường chuẩn bị trước khi triển khai
HO_SO = [
    ("i", "Kế hoạch thực hiện Nghị quyết 01-NQ/ĐU, bộ chỉ tiêu/kế hoạch phát triển kinh tế – xã hội năm 2026"),
    ("ii", "Báo cáo thu, chi ngân sách, dự toán/ước và quyết toán nếu đã có"),
    ("iii", "Danh mục đầy đủ dự án đầu tư công và công trình thi công trên địa bàn, phân định chủ đầu tư"),
    ("iv", "Số liệu an sinh và đô thị"),
    ("v", "Nhu cầu người dùng, chức danh phân quyền, kỳ giao ban"),
    ("vi", "Danh sách nguồn dữ liệu, phần mềm đang sử dụng và khó khăn kết nối"),
]
TT_HO_SO = {"chua_co", "dang_chuan_bi", "da_co"}


def _can_read(u: CurrentUser) -> bool:
    return u.can("doc", "quan_tri") or u.can("duyet", "canh_bao")


def _can_write(u: CurrentUser) -> bool:
    return u.can("duyet", "quan_tri") or u.can("duyet", "canh_bao")


async def _count(s: AsyncSession, q) -> int:  # noqa: ANN001
    return int((await s.execute(q)).scalar() or 0)


async def _real_data(s: AsyncSession, tid: int) -> dict[str, int]:
    """Số bản ghi THẬT (không minh họa) đã xác nhận theo nhóm lõi."""
    from app.budget.models import BudgetLine
    from app.catalog.models import Indicator
    from app.indicators.models import IndicatorValue
    from app.population.models import PopulationStat
    from app.projects.models import Project
    from app.services_pakn.models import AdminServiceStat
    from app.works.models import Work

    iv = select(func.count(IndicatorValue.id)).join(Indicator, Indicator.id == IndicatorValue.indicator_id).where(
        IndicatorValue.tenant_id == tid, IndicatorValue.trang_thai == "da_xac_nhan", IndicatorValue.is_sample.is_(False))
    out = {n: await _count(s, iv.where(Indicator.nhom == n)) for n in TEN_NHOM}
    for n, m in (("ngan_sach", BudgetLine), ("dau_tu_cong", Project), ("cong_trinh", Work), ("dan_cu", PopulationStat), ("tthc_pakn", AdminServiceStat)):
        out[n] += await _count(s, select(func.count(m.id)).where(m.tenant_id == tid, m.is_sample.is_(False)))
    return out


async def _sample_rows(s: AsyncSession, tid: int) -> int:
    from app.core.db import Base, import_models

    import_models()
    n = 0
    for t in Base.metadata.sorted_tables:
        if "is_sample" in t.c and "tenant_id" in t.c:
            n += int((await s.execute(text(f'SELECT count(*) FROM "{t.name}" WHERE tenant_id=:t AND is_sample'), {"t": tid})).scalar() or 0)
    return n


def _kq(ok: bool | None) -> str:
    return "chua_du_du_lieu" if ok is None else ("dat" if ok else "chua_dat")


async def _criteria(s: AsyncSession, tid: int, cfg: dict, today: date) -> tuple[list[dict], dict]:
    from app.budget.models import BudgetLine
    from app.budget.service import api_vs_closed
    from app.compliance.models import ReconciliationMemo
    from app.compliance.service import submission_report
    from app.indicators.models import IndicatorValue
    from app.projects.models import Disbursement
    from app.reports.models import MeetingSession
    from app.sources.service import module_status
    from app.works.models import WorkProgress

    real = await _real_data(s, tid)
    mods = await module_status(s, tid)
    mau = await _sample_rows(s, tid)
    # 1. Tổng quan + dashboard lõi dùng dữ liệu thật đã xác nhận; nhóm khác "đang kết nối"
    thieu_loi = [TEN_NHOM[n] for n in LOI if mods.get(n) != "tat" and not real.get(n)]
    khac = [{"nhom": TEN_NHOM[n], "trang_thai": mods.get(n), "du_lieu_that": real.get(n, 0)} for n in TEN_NHOM if n not in LOI]
    c1 = {"ma": "TC1", "ten": "Có màn hình tổng quan và tối thiểu dashboard lõi sử dụng dữ liệu thật đã xác nhận; các nhóm khác được đánh dấu “đang kết nối” nếu chưa đáp ứng",
          "ket_qua": _kq(not thieu_loi), "chi_tiet": [f"{TEN_NHOM[n]}: {real.get(n, 0)} bản ghi thật đã xác nhận" for n in LOI]
          + [f"{x['nhom']}: {'đang kết nối' if x['trang_thai'] == 'dang_ket_noi' else ('tắt' if x['trang_thai'] == 'tat' else 'đang dùng')}" for x in khac],
          "can_lam": [f"Nhập/đồng bộ và xác nhận số liệu thật nhóm {', '.join(thieu_loi)}"] if thieu_loi else [], "link": "/nguon-du-lieu"}
    # 2. 100% chỉ tiêu công bố có đơn vị cung cấp, kỳ, trạng thái xác nhận, thời điểm cập nhật; 100% truy cập có nhật ký
    pub = IndicatorValue.tenant_id == tid, IndicatorValue.trang_thai == "da_xac_nhan", IndicatorValue.is_sample.is_(False)
    tong_pub = await _count(s, select(func.count(IndicatorValue.id)).where(*pub))
    thieu_ly_lich = await _count(s, select(func.count(IndicatorValue.id)).where(*pub).where(
        (func.coalesce(func.trim(IndicatorValue.don_vi_cung_cap), "") == "") | (func.coalesce(func.trim(IndicatorValue.ky_bao_cao), "") == "")
        | IndicatorValue.thoi_diem_dong_bo.is_(None) | IndicatorValue.nguoi_xac_nhan_ten.is_(None)))
    async with admin_sessionmaker()() as a:
        so_nhat_ky = int((await a.execute(text("SELECT count(*) FROM audit_log WHERE tenant_id=:t"), {"t": tid})).scalar() or 0)
    c2 = {"ma": "TC2", "ten": "100% chỉ tiêu được công bố có đơn vị cung cấp, kỳ số liệu, trạng thái xác nhận và thời điểm cập nhật; 100% truy cập và chỉnh sửa dữ liệu có nhật ký",
          "ket_qua": _kq(None if not tong_pub else thieu_ly_lich == 0),
          "chi_tiet": [f"{tong_pub} số liệu thật đã công bố, {thieu_ly_lich} thiếu thông tin lý lịch",
                       f"Nhật ký truy cập ghi tự động mọi yêu cầu: {so_nhat_ky} bản ghi của đơn vị (chỉ ghi thêm, không sửa/xóa)"],
          "can_lam": [] if tong_pub and not thieu_ly_lich else (["Chưa có số liệu thật được xác nhận"] if not tong_pub else [f"Bổ sung lý lịch cho {thieu_ly_lich} số liệu"]),
          "link": "/chi-tieu"}
    # 3. Ngân sách, giải ngân, công trình khớp hồ sơ hoặc có biên bản giải trình chênh lệch
    kys = [r for r in (await s.execute(select(distinct(BudgetLine.ky)).where(BudgetLine.tenant_id == tid, BudgetLine.is_sample.is_(False),
                                                                             BudgetLine.nguon_loai == "api"))).scalars()]
    memo_refs = {(m.ky, m.ref) for m in (await s.execute(select(ReconciliationMemo).where(ReconciliationMemo.tenant_id == tid,
                                                                                          ReconciliationMemo.doi_tuong == "ngan_sach"))).scalars()}
    lech = 0
    for ky in kys:
        for d in await api_vs_closed(s, tid, int(ky[:4]), ky):
            if (ky, f"{d['loai']}/{d['nhom_ma']}/{d['scope']}") not in memo_refs:
                lech += 1
    gn_cho = await _count(s, select(func.count(Disbursement.id)).where(Disbursement.tenant_id == tid, Disbursement.is_sample.is_(False),
                                                                       Disbursement.trang_thai_xac_nhan != "da_xac_nhan"))
    ct_cho = await _count(s, select(func.count(WorkProgress.id)).where(WorkProgress.tenant_id == tid, WorkProgress.is_sample.is_(False),
                                                                       WorkProgress.trang_thai_xac_nhan != "da_xac_nhan"))
    co_so = real.get("ngan_sach", 0) + real.get("dau_tu_cong", 0) + real.get("cong_trinh", 0)
    c3 = {"ma": "TC3", "ten": "Các chỉ tiêu ngân sách, giải ngân và công trình khớp với số liệu, hồ sơ nghiệp vụ tại kỳ nghiệm thu hoặc có biên bản giải trình chênh lệch",
          "ket_qua": _kq(None if not co_so else (lech == 0 and gn_cho == 0 and ct_cho == 0)),
          "chi_tiet": [f"Ngân sách: {lech} chênh lệch API – báo cáo chốt chưa có biên bản", f"Giải ngân: {gn_cho} kỳ chưa được chủ đầu tư xác nhận",
                       f"Công trình: {ct_cho} lần cập nhật tiến độ chưa xác nhận"],
          "can_lam": ([f"Lập biên bản giải trình {lech} chênh lệch ngân sách"] if lech else []) + ([f"Xác nhận {gn_cho} kỳ giải ngân"] if gn_cho else [])
          + ([f"Xác nhận {ct_cho} cập nhật công trình"] if ct_cho else []), "link": "/ngan-sach"}
    # 4. Nộp đúng hạn theo ngưỡng thống nhất; ghi nhận tỷ lệ thiếu/chậm
    nguong = float(cfg.get("nguong_dung_han", 80))
    tu = date.fromisoformat(cfg["bat_dau"]) if cfg.get("bat_dau") else today - timedelta(days=90)
    rep = await submission_report(s, tid, tu, today, today)
    pct = float(rep["dung_han_pct"]) if rep["dung_han_pct"] is not None else None
    c4 = {"ma": "TC4", "ten": "Các kỳ dữ liệu theo lịch thí điểm được nộp đúng hạn theo ngưỡng được hai bên thống nhất; ghi nhận rõ tỷ lệ thiếu/chậm cập nhật",
          "ket_qua": _kq(None if pct is None else pct >= nguong),
          "chi_tiet": [f"Ngưỡng thống nhất: {nguong:g}% đúng hạn", f"{rep['tong']} kỳ đến hạn từ {tu.strftime('%d/%m/%Y')}: đúng hạn "
                       f"{'—' if pct is None else f'{pct:g}%'}, chậm {rep['cham_pct'] or 0}%, thiếu {rep['thieu_pct'] or 0}%"],
          "can_lam": [f"{x['ten']}: {x['thieu']} kỳ thiếu, {x['cham']} kỳ chậm" for x in rep.get("theo_dau_moi", []) if x["thieu"] or x["cham"]][:6],
          "link": "/nhap-lieu?tab=tuan-thu"}
    # 5. ≥ 02 phiên khai thác phục vụ giao ban có biên bản; không dùng số liệu giả lập làm kết quả thực tế
    phien = list((await s.execute(select(MeetingSession).where(MeetingSession.tenant_id == tid, MeetingSession.file_key.is_not(None))
                                  .order_by(MeetingSession.ngay))).scalars())
    phien_that = [m for m in phien if not (m.noi_dung or {}).get("co_minh_hoa")]
    c5 = {"ma": "TC5", "ten": "Tổ chức tối thiểu 02 phiên khai thác phục vụ giao ban, có biên bản ghi nhận số cảnh báo, giao nhiệm vụ và kết quả xử lý; không sử dụng số liệu giả lập làm kết quả thực tế",
          "ket_qua": _kq(len(phien_that) >= 2 and mau == 0),
          "chi_tiet": [f"{len(phien_that)} phiên có biên bản trên dữ liệu thật ({len(phien)} phiên tổng)" + "".join(f"; {m.ngay.strftime('%d/%m')}: {m.so_canh_bao} cảnh báo, {m.so_giao} giao, {m.so_hoan_thanh} hoàn thành" for m in phien[-3:]),
                       "Không còn dữ liệu minh họa" if mau == 0 else f"Còn {mau} bản ghi dữ liệu minh họa — phải xóa trước khi nghiệm thu"],
          "can_lam": ([f"Tổ chức thêm {2 - len(phien_that)} phiên giao ban có biên bản trên dữ liệu thật"] if len(phien_that) < 2 else [])
          + ([f"Xóa {mau} bản ghi minh họa (Quản trị → Cấu hình đơn vị)"] if mau else []), "link": "/trinh-chieu"}
    ctx = {"real": real, "mods": mods, "mau": mau, "so_phien": len(phien), "so_phien_that": len(phien_that), "rep": rep}
    return [c1, c2, c3, c4, c5], ctx


async def _hints(s: AsyncSession, tid: int, ctx: dict) -> tuple[dict, dict]:
    """Gợi ý tự động: việc trong lộ trình / hồ sơ VI đã có căn cứ trên hệ thống."""
    from app.catalog.models import IndicatorPlan
    from app.dau_moi.models import DauMoi
    from app.projects.models import Project
    from app.sources.models import DataSource
    from app.works.models import Work

    real = ctx["real"]
    ke_hoach_2026 = await _count(s, select(func.count(IndicatorPlan.id)).where(IndicatorPlan.tenant_id == tid, IndicatorPlan.nam == 2026,
                                                                               IndicatorPlan.is_sample.is_(False)))
    dm = list((await s.execute(select(DauMoi).where(DauMoi.tenant_id == tid))).scalars())
    dm_lh = sum(1 for d in dm if d.nguoi_lien_he and (d.dien_thoai or d.email))
    srcs = list((await s.execute(select(DataSource).where((DataSource.tenant_id == tid) | DataSource.tenant_id.is_(None)))).scalars())
    pl_ok = sum(1 for x in srcs if x.phap_ly_chia_se != "chua_cho_phep")
    du_an = await _count(s, select(func.count(Project.id)).where(Project.tenant_id == tid, Project.is_sample.is_(False)))
    ct = await _count(s, select(func.count(Work.id)).where(Work.tenant_id == tid, Work.is_sample.is_(False)))
    async with admin_sessionmaker()() as a:
        n_users = int((await a.execute(text("SELECT count(*) FROM app_user WHERE tenant_id=:t AND trang_thai='hoat_dong'"), {"t": tid})).scalar() or 0)
    viec = {
        "chi_tieu": f"{ke_hoach_2026} kế hoạch chỉ tiêu năm 2026 đã nhập" if ke_hoach_2026 else None,
        "du_an": f"{du_an} dự án thật trên hệ thống" if du_an else None,
        "nguon_nguoi": f"{len(dm)} đầu mối, {dm_lh} đầu mối có người liên hệ",
        "quyen_chia_se": f"{pl_ok}/{len(srcs)} nguồn đã có căn cứ chia sẻ",
        "dashboard_loi": f"{sum(1 for n in LOI if real.get(n))}/5 nhóm lõi có dữ liệu thật",
        "khai_thac": f"{ctx['so_phien']} phiên giao ban có biên bản" if ctx["so_phien"] else None,
        "doi_soat": None,
    }
    ho_so = {
        "i": f"{ke_hoach_2026} kế hoạch chỉ tiêu 2026" if ke_hoach_2026 else None,
        "ii": f"{real.get('ngan_sach', 0)} dòng số liệu ngân sách thật" if real.get("ngan_sach") else None,
        "iii": f"{du_an} dự án, {ct} công trình" if du_an or ct else None,
        "iv": f"{real.get('gd_yt_mt', 0) + real.get('dan_cu', 0)} số liệu an sinh, đô thị" if real.get("gd_yt_mt") or real.get("dan_cu") else None,
        "v": f"{n_users} tài khoản đang hoạt động",
        "vi": f"{len(srcs)} nguồn dữ liệu đã khai báo",
    }
    return {k: v for k, v in viec.items() if v}, {k: v for k, v in ho_so.items() if v}


async def _usage(tid: int, days: int = 30) -> dict:
    """Mức độ sử dụng (DT V.2 ngày 76–90): đăng nhập, người dùng hoạt động, phiên theo vai trò trong N ngày."""
    since = datetime.now(UTC) - timedelta(days=days)
    async with admin_sessionmaker()() as a:
        logins = int((await a.execute(text("SELECT count(*) FROM audit_log WHERE tenant_id=:t AND path='/api/auth/login' AND status=200 AND ts>=:s"),
                                      {"t": tid, "s": since})).scalar() or 0)
        active = int((await a.execute(text("SELECT count(DISTINCT user_id) FROM audit_log WHERE tenant_id=:t AND user_id IS NOT NULL AND ts>=:s"),
                                      {"t": tid, "s": since})).scalar() or 0)
        by_role = (await a.execute(text(
            "SELECT g.role, count(DISTINCT l.user_id) FROM audit_log l JOIN user_grant g ON g.user_id=l.user_id "
            "WHERE l.tenant_id=:t AND l.ts>=:s GROUP BY g.role ORDER BY 2 DESC"), {"t": tid, "s": since})).all()
        thao_tac = int((await a.execute(text("SELECT count(*) FROM audit_log WHERE tenant_id=:t AND method='CHANGE' AND ts>=:s"),
                                        {"t": tid, "s": since})).scalar() or 0)
    return {"so_ngay": days, "so_dang_nhap": logins, "so_nguoi_dung_hoat_dong": active, "so_thao_tac_du_lieu": thao_tac,
            "theo_vai_tro": [{"role": r, "so_nguoi": n} for r, n in by_role]}


@router.get("")
async def pilot(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    if not _can_read(user):
        raise HTTPException(403, "Chỉ lãnh đạo, quản trị đơn vị theo dõi thí điểm")
    tid = s.info["tenant_id"]
    t = await s.get(Tenant, tid)
    cfg = dict((t.config or {}).get("thi_diem") or {})
    today = date.today()
    criteria, ctx = await _criteria(s, tid, cfg, today)
    goi_y_viec, goi_y_ho_so = await _hints(s, tid, ctx)
    bat_dau = date.fromisoformat(cfg["bat_dau"]) if cfg.get("bat_dau") else None
    ngay_thu = (today - bat_dau).days + 1 if bat_dau else None
    done = cfg.get("viec") or {}
    lo_trinh = []
    for ma, a, b, ten, viec in LO_TRINH:
        lo_trinh.append({"ma": ma, "tu_ngay": a, "den_ngay": b, "ten": ten,
                         "tu": (bat_dau + timedelta(days=a - 1)) if bat_dau else None, "den": (bat_dau + timedelta(days=b - 1)) if bat_dau else None,
                         "hien_tai": ngay_thu is not None and a <= ngay_thu <= b, "qua_han": ngay_thu is not None and ngay_thu > b,
                         "viec": [{"ma": v, "ten": vt, "xong": bool(done.get(v)), "goi_y": goi_y_viec.get(v)} for v, vt in viec]})
    hs = cfg.get("ho_so") or {}
    return jsonable({
        "bat_dau": bat_dau, "ngay_thu": ngay_thu, "nguong_dung_han": cfg.get("nguong_dung_han", 80), "lo_trinh": lo_trinh,
        "tieu_chi": criteria, "dat": sum(1 for c in criteria if c["ket_qua"] == "dat"),
        "ho_so": [{"ma": m, "ten": ten, "trang_thai": (hs.get(m) or {}).get("trang_thai", "chua_co"), "ghi_chu": (hs.get(m) or {}).get("ghi_chu", ""),
                   "goi_y": goi_y_ho_so.get(m)} for m, ten in HO_SO],
        "su_dung": await _usage(tid), "co_quyen_sua": _can_write(user), "con_du_lieu_minh_hoa": ctx["mau"] > 0,
    })


class HoSoIn(BaseModel):
    trang_thai: str
    ghi_chu: str = ""


class PilotIn(BaseModel):
    bat_dau: date | None = None
    nguong_dung_han: float | None = Field(None, ge=0, le=100)
    viec: dict[str, bool] | None = None
    ho_so: dict[str, HoSoIn] | None = None


@router.put("")
async def put_pilot(body: PilotIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    if not _can_write(user):
        raise HTTPException(403, "Chỉ lãnh đạo, quản trị đơn vị cập nhật thí điểm")
    tid = s.info["tenant_id"]
    valid_viec = {v for *_, viec in LO_TRINH for v, _ in viec}
    if body.viec and set(body.viec) - valid_viec:
        raise HTTPException(422, "Việc không có trong lộ trình")
    if body.ho_so:
        if set(body.ho_so) - {m for m, _ in HO_SO} or any(h.trang_thai not in TT_HO_SO for h in body.ho_so.values()):
            raise HTTPException(422, "Hồ sơ hoặc trạng thái không hợp lệ")
    async with admin_sessionmaker()() as a:
        t = await a.get(Tenant, tid)
        cfg = dict(t.config or {})
        td = dict(cfg.get("thi_diem") or {})
        before = dict(td)
        if "bat_dau" in body.model_fields_set:
            td["bat_dau"] = body.bat_dau.isoformat() if body.bat_dau else None
        if body.nguong_dung_han is not None:
            td["nguong_dung_han"] = body.nguong_dung_han
        if body.viec:
            td["viec"] = {**(td.get("viec") or {}), **body.viec}
        if body.ho_so:
            td["ho_so"] = {**(td.get("ho_so") or {}), **{k: v.model_dump() for k, v in body.ho_so.items()}}
        cfg["thi_diem"] = td
        t.config = cfg
        await a.commit()
    await record_change(user, tid, f"don_vi:{tid}:thi_diem", before, td)
    return {"ok": True}
