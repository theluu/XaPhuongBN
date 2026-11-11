"""Màn hình Tổng quan (DT IV.1): ① chỉ tiêu trọng tâm ② việc cần chỉ đạo trong tuần ③ xu hướng + bản đồ ④ lịch cập nhật & xác nhận."""
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.router import week
from app.auth.deps import get_current_user, tenant_db
from app.budget.models import BudgetLine
from app.budget.service import summary as budget_summary
from app.catalog.cycles import DEFAULT_CYCLES
from app.catalog.models import Indicator
from app.core.db import admin_sessionmaker
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.indicators.models import IndicatorValue
from app.indicators.service import card, completeness
from app.platform.models import ResidentialGroup, Tenant
from app.platform.router import agency_name, sample_flag
from app.population.models import PopulationStat
from app.projects.models import Disbursement, Project
from app.projects.service import summary as project_summary
from app.services_pakn.models import AdminServiceStat, FeedbackTicket
from app.services_pakn.service import pakn_summary, tthc_summary
from app.sources.service import module_status
from app.works.models import Work, WorkProgress
from app.works.service import valid_points

router = APIRouter(prefix="/api", tags=["tong-quan"])
TEN_NHOM = {"ktxh": "Chỉ tiêu KT-XH, Nghị quyết", "dan_cu": "Dân cư thống kê tổng hợp", "ngan_sach": "Thu, chi ngân sách",
            "dau_tu_cong": "Đầu tư công chi tiết", "cong_trinh": "Công trình, dự án xây dựng", "tthc_pakn": "TTHC, phản ánh kiến nghị",
            "gd_yt_mt": "Giáo dục, y tế, môi trường"}
CHU_KY = {"ktxh": "Tháng/quý/năm", "dan_cu": "Hằng tháng", "ngan_sach": "Tuần/tháng", "dau_tu_cong": "Hằng tuần", "cong_trinh": "Hằng tuần",
          "tthc_pakn": "API và báo cáo kỳ", "gd_yt_mt": "Tháng/quý"}
HAN_NGAY = {"dan_cu": 35, "ngan_sach": 34, "dau_tu_cong": 10, "cong_trinh": 10, "tthc_pakn": 7}


def tile(ma: str, ten: str, gia_tri, don_vi: str, ky: str, link: str, nhom: str, *, ke_hoach=None, muc_so_sanh=None,  # noqa: ANN001
         hoan_thanh=None, status: str = "theo_doi", data_state: str = "da_xac_nhan", nguon: str = "", don_vi_cung_cap: str = "",
         ghi_chu: str = "", is_sample: bool = False, thoi_diem_chot=None) -> dict:  # noqa: ANN001
    """Ô chỉ số tổng hợp cùng cấu trúc với thẻ chỉ tiêu để giao diện dùng chung (có lý lịch nguồn)."""
    return {"id": 0, "ma": ma, "ten": ten, "nhom": nhom, "phan_he": nhom, "bo": [], "don_vi": don_vi, "chieu": "tang_tot", "ky": ky,
            "ke_hoach": ke_hoach, "muc_tieu": None, "muc_tieu_khoang": None, "nguong_toan_tu": None, "muc_tieu_2030": None,
            "muc_so_sanh": muc_so_sanh, "thuc_hien": gia_tri, "du_bao": None, "hoan_thanh_pct": hoan_thanh, "status": status,
            "data_state": data_state if gia_tri is not None else "chua_co_qua_han", "ky_truoc": {"ky": "", "gia_tri": None},
            "cung_ky": {"ky": "", "gia_tri": None}, "nguon": nguon, "nguon_loai": None, "don_vi_cung_cap": don_vi_cung_cap,
            "nguoi_xac_nhan": None, "thoi_diem_chot": thoi_diem_chot, "thoi_diem_dong_bo": None, "lech_nguon": None,
            "co_so_moi_cho_xac_nhan": False, "is_sample": is_sample, "phan_loai_thong_tin": "noi_bo", "ky_cap_nhat": "thang",
            "value_id": None, "link": link, "ghi_chu": ghi_chu}


def _bil(v):  # noqa: ANN001, ANN202
    return None if v is None else round(float(v) / 1e9, 1)


async def _tiles(s: AsyncSession, user: CurrentUser, tid: int, ky: str, tdp: int | None, allow_tdp: bool, today: date) -> list[dict]:
    out = []
    if user.can("doc", "ngan_sach"):
        b = await budget_summary(s, tid, int(ky[:4]), ky, {})
        for ma, scope, ten in (("NS-THU-DB", "dia_ban", "Thu ngân sách trên địa bàn"), ("NS-THU-NSP", "ns_phuong", "Thu ngân sách phường được hưởng")):
            t = b["thu"][scope]
            st = "chua_du_du_lieu" if t["thuc_hien"] is None or t["ke_hoach_ky"] is None else ("dat" if t["thuc_hien"] >= t["ke_hoach_ky"] else "nguy_co")
            out.append(tile(ma, ten, _bil(t["thuc_hien"]), "tỷ đồng", ky, "/ngan-sach", "ngan_sach", ke_hoach=_bil(t["ke_hoach_ky"]),
                            muc_so_sanh=_bil(t["ke_hoach_ky"]), hoan_thanh=float(t["ty_le_pct"]) if t["ty_le_pct"] is not None else None, status=st,
                            data_state="tam_thoi" if b["cho_doi_soat"] else "da_xac_nhan", nguon="Báo cáo thu ngân sách",
                            don_vi_cung_cap="Bộ phận Tài chính – Kế toán", ghi_chu=f"Dự toán năm {_bil(t['du_toan'])} tỷ đồng",
                            is_sample=b["is_sample"], thoi_diem_chot=b["ngay_chot_gan_nhat"]))
    if user.can("doc", "dau_tu_cong"):
        p = await project_summary(s, tid, ky)
        l1 = p["theo_lop"]["1"]
        out.append(tile("DTC-GN", "Giải ngân đầu tư công (phường làm chủ đầu tư)", float(p["ty_le_giai_ngan_ns_phuong"]) if p["ty_le_giai_ngan_ns_phuong"] is not None else None,
                        "%", ky, "/dau-tu-cong", "dau_tu_cong", status="nguy_co" if l1["so_cham"] else "dat",
                        nguon="Chủ đầu tư báo cáo, Kho bạc đối soát", don_vi_cung_cap="Ban quản lý dự án phường",
                        ghi_chu=f"{l1['so_du_an']} dự án, {l1['so_cham']} dự án chậm so với lịch vốn", is_sample=p["is_sample"]))
    if user.can("doc", "dan_cu"):
        q = select(func.sum(PopulationStat.gia_tri)).where(PopulationStat.tenant_id == tid, PopulationStat.ky == ky, PopulationStat.chi_so == "nhan_khau")
        ten = "Dân số"
        if tdp and allow_tdp:
            q = q.where(PopulationStat.tdp_id == tdp)
            g = await s.get(ResidentialGroup, tdp)
            ten = f"Dân số {g.ten}" if g else ten
        else:
            q = q.where(PopulationStat.tdp_id.is_(None), PopulationStat.gioi != "")
        v = (await s.execute(q)).scalar()
        out.append(tile("DC-DAN-SO", ten, float(v) if v is not None else None, "người", ky, "/dan-cu", "dan_cu",
                        nguon="Kho dữ liệu dùng chung (API dân cư)", don_vi_cung_cap="Công an thành phố"))
    inds = {i.ma_chi_tieu: i for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tid, Indicator.ma_chi_tieu.in_(["NQ01-10", "NQ01-12"])))).scalars()}
    for ma in ("NQ01-10", "NQ01-12"):
        if ma in inds and user.can("doc", inds[ma].nhom):
            c = await card(s, inds[ma], ky)
            c["link"] = f"/chi-tieu?ma={ma}"
            out.append(c)
    if user.can("doc", "tthc_pakn"):
        tt = await tthc_summary(s, tid, today - timedelta(days=30), today, "thang", None)
        dh = tt["tong"]["dung_han_pct"]
        out.append(tile("TTHC-DH", "Hồ sơ TTHC giải quyết đúng hạn (30 ngày)", float(dh) if dh is not None else None, "%", ky, "/hanh-chinh", "tthc_pakn",
                        status="dat" if dh is not None and dh >= 98 else ("nguy_co" if dh is not None else "chua_du_du_lieu"), muc_so_sanh=98,
                        data_state="tam_thoi" if tt["co_so_tam_thoi"] else "da_xac_nhan", nguon="Biểu mẫu động (luồng DVCQG gián đoạn)",
                        don_vi_cung_cap="Bộ phận Một cửa", ghi_chu=f"{tt['tong']['tiep_nhan']} hồ sơ tiếp nhận", is_sample=tt["is_sample"]))
        pk = await pakn_summary(s, tid, today - timedelta(days=90), today, today)
        out.append(tile("PAKN-QH", "Phản ánh kiến nghị quá hạn", float(pk["theo_trang_thai"]["qua_han"]), "phản ánh", ky, "/hanh-chinh", "tthc_pakn",
                        status="nguy_co" if pk["theo_trang_thai"]["qua_han"] else "dat", nguon="Hệ thống phản ánh kiến nghị (API)",
                        don_vi_cung_cap="Hệ thống PAKN thành phố", ghi_chu=f"{pk['tong']} phản ánh trong 90 ngày", is_sample=pk["is_sample"]))
    return out


async def _schedule(s: AsyncSession, user: CurrentUser, tid: int, ky: str, today: date, don_vi: str | None) -> list[dict]:
    rows = []
    last = {
        "ngan_sach": (await s.execute(select(func.max(BudgetLine.ngay_chot)).where(BudgetLine.tenant_id == tid))).scalar(),
        "dan_cu": (await s.execute(select(func.max(PopulationStat.ky)).where(PopulationStat.tenant_id == tid))).scalar(),
        "dau_tu_cong": (await s.execute(select(func.max(Disbursement.ky)).where(Disbursement.tenant_id == tid))).scalar(),
        "cong_trinh": (await s.execute(select(func.max(WorkProgress.ngay)).where(WorkProgress.tenant_id == tid))).scalar(),
        "tthc_pakn": (await s.execute(select(func.max(AdminServiceStat.ngay)).where(AdminServiceStat.tenant_id == tid))).scalar(),
    }
    for nhom, ten in TEN_NHOM.items():
        if not user.can("doc", nhom):
            continue
        if nhom in ("ktxh", "gd_yt_mt"):
            inds = list((await s.execute(select(Indicator).where(Indicator.tenant_id == tid, Indicator.phan_he == nhom))).scalars())
            for dv in sorted({i.don_vi_chu_quan for i in inds}):
                if don_vi and dv != don_vi:
                    continue
                cs = [await card(s, i, ky) for i in inds if i.don_vi_chu_quan == dv]
                n = len(cs)
                xn = sum(c["data_state"] == "da_xac_nhan" for c in cs)
                tam = sum(c["data_state"] == "tam_thoi" for c in cs)
                rows.append({"nhom": nhom, "ten": ten, "don_vi": dv, "chu_ky": CHU_KY[nhom], "dieu_kien": DEFAULT_CYCLES[nhom]["dieu_kien"],
                             "so_chi_tieu": n, "da_xac_nhan": xn, "tam_thoi": tam, "chua_co": n - xn - tam,
                             "data_state": "chua_co_qua_han" if n - xn - tam else ("tam_thoi" if tam else "da_xac_nhan"), "cap_nhat_cuoi": None})
            continue
        if don_vi:
            continue
        lv = last.get(nhom)
        if isinstance(lv, str):
            y, m = int(lv[:4]), int(lv[5:7])
            lv = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
        if isinstance(lv, datetime):
            lv = lv.astimezone(UTC).date()
        state = "chua_co_qua_han" if lv is None or (today - lv).days > HAN_NGAY[nhom] else "da_xac_nhan"
        rows.append({"nhom": nhom, "ten": ten, "don_vi": None, "chu_ky": CHU_KY[nhom], "dieu_kien": DEFAULT_CYCLES[nhom]["dieu_kien"],
                     "cap_nhat_cuoi": lv, "data_state": state})
    return rows


@router.get("/overview")
async def overview(ky: str = Query(default_factory=lambda: date.today().strftime("%Y-%m")), tdp: int | None = None, don_vi: str | None = None,
                   che_do: str = "lam_viec", s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    tid, today = s.info["tenant_id"], date.today()
    async with admin_sessionmaker()() as adm:
        t = await adm.get(Tenant, tid)
        modules = await module_status(adm, tid)
    allow_tdp = bool((t.config or {}).get("cho_phep_theo_tdp"))
    present = che_do == "trinh_chieu"
    tiles = [x for x in await _tiles(s, user, tid, ky, tdp, allow_tdp, today) if not (present and x.get("phan_loai_thong_tin") == "han_che")]
    nq = [await card(s, i, ky) for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tid))).scalars()
          if "NQ01" in (i.bo or []) and user.can("doc", i.nhom)]
    chi_dao = await week(s, user)
    if present:
        chi_dao = [{**a, "mo_ta": "", "ho_so": None} for a in chi_dao]
    feats, lop = [], []
    if user.can("doc", "dau_tu_cong") or user.can("doc", "cong_trinh"):
        lop = ["du_an", "cong_trinh"]
        for p in (await s.execute(select(Project).where(Project.tenant_id == tid, Project.lat.is_not(None)))).scalars():
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(p.lng), float(p.lat)]},
                          "properties": {"ma": p.ma_du_an, "ten": p.ten, "loai": "du_an", "lop": p.lop, "link": f"/dau-tu-cong/{p.ma_du_an}"}})
        for w in await valid_points(s, tid):
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(w.lng), float(w.lat)]},
                          "properties": {"ma": w.ma_cong_trinh, "ten": w.ten, "loai": "cong_trinh", "link": f"/cong-trinh/{w.ma_cong_trinh}"}})
    trend = []
    if user.can("doc", "ngan_sach"):
        b = await budget_summary(s, tid, int(ky[:4]), ky, {})
        trend = [{"ky": x["ky"], "thuc_hien": _bil(x["thu_dia_ban"]), "ke_hoach": _bil(x["ke_hoach_thu_dia_ban"])} for x in b["xu_huong_thang"]]
    groups = [g for g in ("ktxh", "gd_yt_mt", "dan_cu", "cong_trinh") if user.can("doc", g)]
    full = [await completeness(s, tid, g, ky) for g in groups]
    du_kien = sum(c["du_kien"] for c in full)
    tdps = [{"id": g.id, "ten": g.ten} for g in (await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == tid).order_by(ResidentialGroup.ma_tdp))).scalars()] if allow_tdp else []
    dvs = sorted({i.don_vi_chu_quan for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tid))).scalars()})
    return jsonable({
        "tenant": {"ten": t.ten, "ten_co_quan": agency_name(t)}, "ky": ky, "che_do": che_do,
        "co_du_lieu_minh_hoa": (await sample_flag(s))["co_du_lieu_minh_hoa"], "modules": modules,
        "the_chi_so": tiles,
        "nq01": {"tong": len(nq), **{k: sum(c["status"] == k for c in nq) for k in ("dat", "nguy_co", "chua_du_du_lieu")}},
        "can_chi_dao": chi_dao, "xu_huong": trend, "ban_do": {"type": "FeatureCollection", "features": feats, "lop": lop},
        "lich_cap_nhat": await _schedule(s, user, tid, ky, today, don_vi),
        "do_day_du": {"du_kien": du_kien, "co_so": sum(c["co_so"] for c in full),
                      "ty_le_pct": round(sum(c["co_so"] for c in full) * 100 / du_kien, 1) if du_kien else None},
        "bo_loc": {"tdp": tdps, "don_vi": dvs},
    })
