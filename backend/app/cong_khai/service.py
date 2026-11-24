"""Trang công khai theo phường: cấu hình chọn chỉ tiêu, dựng bản công bố kỳ, nhận diện phường theo tên miền.

Nguyên tắc:
- Chỉ những chỉ tiêu phường chọn công khai mới ra ngoài; chỉ tiêu phân loại "hạn chế" không bao giờ được chọn.
- Chỉ số liệu ĐÃ XÁC NHẬN mới có giá trị trên trang công khai; số tạm thời/chờ đối soát hiện "đang cập nhật".
- Trang công khai đọc bản công bố đã chụp, không đọc trực tiếp số liệu nội bộ.
"""
import re
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import Indicator
from app.core.db import tenant_session
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.indicators.service import card
from app.platform.models import Tenant
from app.platform.router import agency_name

# Ô tổng hợp có thể công khai (mã ô ở màn hình Tổng quan)
TONG_HOP = {
    "NS-THU-DB": "Thu ngân sách trên địa bàn",
    "NS-THU-NSP": "Thu ngân sách phường được hưởng",
    "DTC-GN": "Giải ngân đầu tư công",
    "DC-DAN-SO": "Dân số",
    "TTHC-DH": "Hồ sơ TTHC giải quyết đúng hạn",
    "PAKN-QH": "Phản ánh kiến nghị quá hạn",
}
TONG_HOP_MAC_DINH = ["NS-THU-DB", "DTC-GN", "DC-DAN-SO", "TTHC-DH", "PAKN-QH"]
# Chuyên mục biểu đồ trên trang công khai (số liệu tổng hợp, không có thông tin cá nhân hay nội dung xử lý nội bộ)
CHUYEN_MUC = {"chi_dao": "Chỉ đạo – điều hành", "phuc_vu": "Chỉ số phục vụ người dân", "ngan_sach": "Thu – chi ngân sách",
              "dich_vu_cong": "Dịch vụ công", "phan_anh": "Phản ánh kiến nghị",
              "dau_tu_cong": "Đầu tư công", "cong_trinh": "Công trình xây dựng", "dan_cu": "Dân cư"}
LINH_VUC_PAKN = {"moi_truong": "Vệ sinh môi trường", "trat_tu_do_thi": "Trật tự đô thị", "ha_tang": "Hạ tầng", "an_ninh": "An ninh trật tự",
                 "dat_dai": "Đất đai, xây dựng"}
TRANG_THAI_VAN_DE = {"moi": "Mới phát hiện", "da_giao": "Đã giao xử lý", "dang_xu_ly": "Đang xử lý", "gia_han": "Gia hạn", "hoan_thanh": "Hoàn thành"}
MUC_DO = {"cao": "Mức cao", "trung_binh": "Mức trung bình", "thap": "Mức thấp"}
HAI_LONG = {5: "Rất hài lòng", 4: "Hài lòng", 3: "Bình thường", 2: "Chưa hài lòng", 1: "Không hài lòng"}
# Bộ chỉ số phục vụ người dân, doanh nghiệp (QĐ 766/QĐ-TTg) — 5 nhóm, tổng 100 điểm; điểm tối đa lưu kèm số liệu để điều chỉnh được
PHUC_VU_MAC_DINH = [("Công khai, minh bạch", 18), ("Tiến độ giải quyết", 20), ("Dịch vụ công trực tuyến", 22), ("Mức độ hài lòng", 18), ("Số hóa hồ sơ", 22)]
TRANG_THAI_PAKN = {"hoan_thanh": "Đã giải quyết", "dang_xu_ly": "Đang xử lý", "tiep_nhan": "Mới tiếp nhận", "qua_han": "Quá hạn"}
TEN_PHAN_HE = {"ktxh": "Kinh tế – xã hội", "gd_yt_mt": "Giáo dục, y tế, môi trường", "ngan_sach": "Ngân sách",
               "dau_tu_cong": "Đầu tư công", "dan_cu": "Dân cư", "tthc_pakn": "Hành chính công", "cong_trinh": "Công trình"}
# Trường được phép ra ngoài của một thẻ chỉ tiêu (lọc theo danh sách trắng)
FIELDS = ("ma", "ten", "phan_he", "don_vi", "ky", "ke_hoach", "muc_tieu", "muc_so_sanh", "thuc_hien", "hoan_thanh_pct", "status",
          "nguon", "don_vi_cung_cap", "thoi_diem_chot", "ghi_chu", "chieu")
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")
HOST_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
PUBLIC_VIEWER = CurrentUser(id=0, tenant_id=None, tenant_ids=[], roles=set(), permissions={"*": {"doc"}}, username="cong_khai")


def slug_of(t: Tenant) -> str | None:
    return (t.config or {}).get("slug")


def domains_of(t: Tenant) -> list[str]:
    return list((t.config or {}).get("ten_mien") or [])


def norm_host(h: str | None) -> str:
    return (h or "").split(",")[0].strip().lower().split(":")[0].rstrip(".")


async def wards(adm: AsyncSession) -> list[Tenant]:
    q = select(Tenant).where(Tenant.cap.in_(("xa", "phuong")), Tenant.trang_thai == "hoat_dong").order_by(Tenant.ten)
    return list((await adm.execute(q)).scalars())


async def tenant_for_host(adm: AsyncSession, host: str | None) -> Tenant | None:
    h = norm_host(host)
    if not h:
        return None
    for t in await wards(adm):
        if h in domains_of(t):
            return t
    return None


async def tenant_for_slug(adm: AsyncSession, slug: str) -> Tenant | None:
    for t in await wards(adm):
        if slug_of(t) == slug:
            return t
    return None


def public_config(t: Tenant, inds: list[Indicator]) -> dict:
    """Cấu hình công khai hiện hành; mặc định = chỉ tiêu phân loại 'công khai' + các ô tổng hợp chính."""
    cfg = (t.config or {}).get("cong_khai") or {}
    allowed = {i.ma_chi_tieu for i in inds if i.phan_loai_thong_tin != "han_che"}
    chi_tieu = cfg.get("chi_tieu")
    if chi_tieu is None:
        chi_tieu = [i.ma_chi_tieu for i in inds if i.phan_loai_thong_tin == "cong_khai"]
    return {
        "chi_tieu": [m for m in chi_tieu if m in allowed],
        "tong_hop": [m for m in (cfg.get("tong_hop") if cfg.get("tong_hop") is not None else TONG_HOP_MAC_DINH) if m in TONG_HOP],
        "xu_huong_ngan_sach": bool(cfg.get("xu_huong_ngan_sach", True)),
        "chuyen_muc": [m for m in (cfg.get("chuyen_muc") if cfg.get("chuyen_muc") is not None else list(CHUYEN_MUC)) if m in CHUYEN_MUC],
        "gioi_thieu": cfg.get("gioi_thieu") or "",
    }


def period_bounds(ky: str, today: date | None = None) -> tuple[date, date, str]:
    """(ngày đầu, ngày cuối, tháng đại diện YYYY-MM) của kỳ tháng/quý/năm; tháng đại diện không vượt tháng hiện tại."""
    today = today or date.today()
    if re.fullmatch(r"\d{4}-\d{2}", ky):
        start = date(int(ky[:4]), int(ky[5:7]), 1)
        end_m = ky
    elif m := re.fullmatch(r"(\d{4})-Q([1-4])", ky):
        y, q = int(m[1]), int(m[2])
        start, end_m = date(y, 3 * q - 2, 1), f"{y}-{3 * q:02d}"
    elif re.fullmatch(r"\d{4}", ky):
        start, end_m = date(int(ky), 1, 1), f"{ky}-12"
    else:
        raise ValueError(ky)
    cur = today.strftime("%Y-%m")
    km = min(end_m, cur) if start <= today else end_m
    return start, _month_end(end_m), km


async def _confirmed_value(s: AsyncSession, ind: Indicator, ky: str) -> float | None:
    from app.indicators.service import _resolve, _rows

    v, state, _ = _resolve(ind, await _rows(s, ind.id, ky, ind.scope))
    return float(v.gia_tri) if v is not None and state == "da_xac_nhan" and v.gia_tri is not None else None


def _public_card(c: dict) -> dict:
    out = {k: c.get(k) for k in FIELDS}
    confirmed = c.get("data_state") == "da_xac_nhan" and c.get("thuc_hien") is not None
    out["da_xac_nhan"] = confirmed
    if not confirmed:  # số tạm thời / chờ đối soát / chưa có → không ra ngoài
        out.update(thuc_hien=None, hoan_thanh_pct=None, status="dang_cap_nhat", thoi_diem_chot=None)
    out["ten_phan_he"] = TEN_PHAN_HE.get(c.get("phan_he") or "", "Khác")
    return out


async def build_snapshot(tid: int, ky: str) -> dict:
    """Dựng bản công bố kỳ `ky` cho đơn vị `tid` theo cấu hình công khai (chỉ giữ số đã xác nhận)."""
    from app.budget.service import summary as budget_summary
    from app.overview.router import _bil, _tiles

    today = date.today()
    start, end, km = period_bounds(ky, today)
    async with tenant_session([tid]) as s:
        s.info["tenant_id"] = tid
        t = await s.get(Tenant, tid)
        assert t is not None
        inds = list((await s.execute(select(Indicator).where(Indicator.tenant_id == tid).order_by(Indicator.ma_chi_tieu))).scalars())
        cfg = public_config(t, inds)
        by_ma = {i.ma_chi_tieu: i for i in inds}
        raw_cards = [await card(s, by_ma[m], ky) for m in cfg["chi_tieu"] if m in by_ma]
        chi_tieu = []
        for c in raw_cards:
            pc = _public_card(c)
            ind = by_ma[c["ma"]]
            pc["so_sanh"] = {k: {"ky": c[k]["ky"], "gia_tri": await _confirmed_value(s, ind, c[k]["ky"]) if c[k].get("ky") else None}
                             for k in ("ky_truoc", "cung_ky")} if pc["da_xac_nhan"] else None
            chi_tieu.append(pc)
        # chỉ số theo cửa sổ thời gian (TTHC 30 ngày, PAKN 90 ngày) tính đến cuối kỳ công bố, không lấy số tạm thời của tuần hiện tại
        tile_cache: dict[str, dict[str, dict]] = {}

        async def tiles_at(mk: str) -> dict[str, dict]:
            if mk not in tile_cache:
                tile_cache[mk] = {x["ma"]: x for x in await _tiles(s, PUBLIC_VIEWER, tid, mk, None, False, min(_month_end(mk), today))}
            return tile_cache[mk]

        tiles_all = await tiles_at(km)
        tong_hop = []
        for m in cfg["tong_hop"]:
            if m not in tiles_all:
                continue
            pc, mk = _public_card(tiles_all[m]), km
            # Số liệu nổi bật không để "Đang cập nhật": kỳ này chưa xác nhận → dùng số đã xác nhận của tháng gần nhất (ghi rõ tháng)
            for back in range(1, 13):
                if pc["da_xac_nhan"]:
                    break
                mk = _shift(km, -back)
                if m in (prev := await tiles_at(mk)):
                    pc = _public_card(prev[m])
            if not pc["da_xac_nhan"]:
                pc, mk = _public_card(tiles_all[m]), km
            pc["ten"] = TONG_HOP[m] if m == "DTC-GN" else pc["ten"]
            pc["ky_so_lieu"] = mk if mk != km else None
            tong_hop.append(pc)
        chuyen_muc = await _chuyen_muc(s, tid, ky, cfg["chuyen_muc"], t, start, end, km)
        diem = await _points(s, tid)
        xu_huong = []
        if cfg["xu_huong_ngan_sach"]:
            b = await budget_summary(s, tid, int(km[:4]), km, {})
            if not b["cho_doi_soat"]:
                xu_huong = [{"ky": x["ky"], "thuc_hien": _bil(x["thu_dia_ban"]), "ke_hoach": _bil(x["ke_hoach_thu_dia_ban"])}
                            for x in b["xu_huong_thang"]]
    co_minh_hoa = (any(c.get("is_sample") for c in raw_cards) or any(x.get("is_sample") for x in tiles_all.values())
                   or any(v.get("is_sample") for v in chuyen_muc.values()))
    shown = chi_tieu + tong_hop
    return jsonable({
        "ky": ky, "don_vi": {"ten": t.ten, "ten_co_quan": agency_name(t)},
        "ban_do": {k: v for k, v in ((t.config or {}).get("ban_do") or {}).items() if k in ("tam", "zoom", "tile_url")},
        "gioi_thieu": cfg["gioi_thieu"], "tong_hop": tong_hop, "chi_tieu": chi_tieu, "xu_huong_ngan_sach": xu_huong, "chuyen_muc": chuyen_muc, "diem": diem,
        "tu_ngay": start, "den_ngay": end,
        "thong_ke": {"so_chi_tieu": len(shown), "da_xac_nhan": sum(c["da_xac_nhan"] for c in shown),
                     "dat": sum(c["status"] == "dat" for c in shown), "nguy_co": sum(c["status"] == "nguy_co" for c in shown)},
        "co_minh_hoa": co_minh_hoa, "dung_luc": datetime.now(UTC),
    })


def _f(v):  # noqa: ANN001, ANN202
    return None if v is None else float(v)


def _ty(v):  # noqa: ANN001, ANN202
    return None if v is None else round(float(v) / 1e9, 2)


def _month_end(ky: str) -> date:
    y, m = int(ky[:4]), int(ky[5:7])
    return date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def _shift(ky: str, n: int) -> str:
    y, m = int(ky[:4]), int(ky[5:7]) - 1 + n
    return f"{y + m // 12}-{m % 12 + 1:02d}"


async def _points(s: AsyncSession, tid: int) -> list[dict]:
    """Điểm trường học, trạm y tế, điểm môi trường đã được phép hiển thị."""
    from app.quality_of_life.models import PointOfInterest

    q = select(PointOfInterest).where(PointOfInterest.tenant_id == tid, PointOfInterest.cho_phep_hien_thi.is_(True))
    return [{"loai": p.loai, "ten": p.ten, "lat": _f(p.lat), "lng": _f(p.lng)} for p in (await s.execute(q)).scalars()]


async def _chuyen_muc(s: AsyncSession, tid: int, ky: str, chon: list[str], t: Tenant, start: date, end: date, km: str) -> dict:  # noqa: C901, PLR0912, PLR0915
    """Số liệu tổng hợp cho các biểu đồ công khai. Chỉ lấy phần đã chốt/đối soát/xác nhận; không có tên người, nội dung xử lý nội bộ."""
    from app.budget.service import summary as budget_summary
    from app.platform.models import SharedCatalog
    from app.population.service import population
    from app.projects.service import list_projects
    from app.services_pakn.service import pakn_summary, tthc_summary
    from app.works.models import Work, WorkProgress

    ten = {c.ma: c.ten for c in (await s.execute(select(SharedCatalog))).scalars()}
    out: dict = {}
    is_month = len(ky) == 7 and "Q" not in ky
    if "chi_dao" in chon:
        out_cd = await _chi_dao(s, tid, end, ten)
        if out_cd:
            out["chi_dao"] = out_cd
    if "phuc_vu" in chon:
        pv = _phuc_vu(t, km)
        if pv:
            out["phuc_vu"] = pv
    if "ngan_sach" in chon:
        nam = int(km[:4])
        b, k = None, km
        while k[:4] == str(nam):  # tháng gần nhất đã đối soát với Kho bạc
            x = await budget_summary(s, tid, nam, k, ten)
            if x["co_du_lieu"] and not x["cho_doi_soat"]:
                b = x
                break
            k = _shift(k, -1)
        if b:
            tot = lambda t: {"du_toan": _ty(t["du_toan"]), "thuc_hien": _ty(t["thuc_hien"]), "ty_le_pct": _f(t["ty_le_pct"])}  # noqa: E731
            out["ngan_sach"] = {
                "ky": b["ky"], "thu_dia_ban": tot(b["thu"]["dia_ban"]), "thu_ns_phuong": tot(b["thu"]["ns_phuong"]), "chi": tot(b["chi"]["tong_hop"]),
                "co_cau_thu": [{"ten": x["ten"], "thuc_hien": _ty(x["thuc_hien"]), "du_toan": _ty(x["du_toan"]), "ty_le_pct": _f(x["ty_le_pct"])}
                               for x in b["nhom_thu"] if x["scope"] == "dia_ban"],
                "co_cau_chi": [{"ten": x["ten"], "thuc_hien": _ty(x["thuc_hien"]), "du_toan": _ty(x["du_toan"]), "ty_le_pct": _f(x["ty_le_pct"])}
                               for x in b["chi"]["theo_nhom"]],
                "xu_huong": [{"ky": x["ky"], "thu": _ty(x["thu_dia_ban"]), "ke_hoach": _ty(x["ke_hoach_thu_dia_ban"]), "chi": _ty(x["chi"])}
                             for x in b["xu_huong_thang"]],
                "is_sample": b["is_sample"],
            }
    if "dich_vu_cong" in chon:
        t0 = date(int(_shift(km, -5)[:4]), int(_shift(km, -5)[5:7]), 1) if is_month else start
        tt = await tthc_summary(s, tid, t0, end, "thang", None)
        if tt["tong"]["tiep_nhan"]:
            keep = ("tiep_nhan", "giai_quyet", "dung_han", "qua_han", "truc_tuyen", "dung_han_pct", "truc_tuyen_pct")
            out["dich_vu_cong"] = {
                "tu": t0, "den": end, "tong": {k: _f(tt["tong"][k]) for k in keep},
                "theo_thang": [{"ky": x["ky"], **{k: _f(x[k]) for k in keep}} for x in tt["theo_ky"]],
                "theo_bo_phan": [{"ten": x["bo_phan"], **{k: _f(x[k]) for k in keep}} for x in tt["theo_bo_phan"]],
                "co_so_tam_thoi": tt["co_so_tam_thoi"], "is_sample": tt["is_sample"],
            }
    if "phan_anh" in chon:
        p0 = end - timedelta(days=89) if is_month else start
        pk = await pakn_summary(s, tid, p0, end, end)
        if pk["tong"]:
            extra = await _pakn_extra(s, tid, p0, end)
            out["phan_anh"] = {
                "tu": p0, "den": end, "tong": pk["tong"], **extra,
                "theo_trang_thai": [{"ma": k, "ten": TRANG_THAI_PAKN.get(k, k), "so": v} for k, v in pk["theo_trang_thai"].items()],
                "theo_linh_vuc": sorted([{"ten": LINH_VUC_PAKN.get(x["linh_vuc"], x["linh_vuc"]), "tong": x["tong"], "qua_han": x["qua_han"]}
                                         for x in pk["theo_linh_vuc"]], key=lambda x: -x["tong"]),
                "ty_le_dung_han_pct": _f(pk["ty_le_dung_han_pct"]), "ty_le_da_tra_loi_pct": _f(pk["ty_le_da_tra_loi_pct"]),
                "hai_long_tb": _f(pk["hai_long_tb"]), "is_sample": pk["is_sample"],
            }
    if "dau_tu_cong" in chon:
        rows = [r for r in await list_projects(s, tid, km) if r["lop"] in (1, 2)]
        if rows:
            ds = [{"ten": r["ten"], "lop": r["lop"], "lop_ten": r["lop_ten"], "chu_dau_tu": r["chu_dau_tu"], "ke_hoach_von": _ty(r["ke_hoach_von_nam"]),
                   "giai_ngan": _ty(r["giai_ngan_luy_ke"]) if r["trang_thai_xac_nhan"] == "da_xac_nhan" else None,
                   "ty_le_pct": _f(r["ty_le_giai_ngan_pct"]) if r["trang_thai_xac_nhan"] == "da_xac_nhan" else None,
                   "khoi_luong_pct": _f(r["khoi_luong_pct"]) if r["trang_thai_xac_nhan"] == "da_xac_nhan" else None,
                   "tong_muc_dt": _ty(r["tong_muc_dt"]), "ngay_ht": r["ngay_ht_ke_hoach"], "lat": _f(r["lat"]), "lng": _f(r["lng"])} for r in rows]
            okv = [d for d in ds if d["ke_hoach_von"] is not None and d["giai_ngan"] is not None]
            kh, gn = sum(d["ke_hoach_von"] for d in okv), sum(d["giai_ngan"] for d in okv)
            out["dau_tu_cong"] = {"so_du_an": len(ds), "ke_hoach_von": round(kh, 2), "giai_ngan": round(gn, 2),
                                  "ty_le_pct": round(gn * 100 / kh, 1) if kh else None, "du_an": ds,
                                  "is_sample": any(r["is_sample"] for r in rows)}
    if "cong_trinh" in chon:
        ws = list((await s.execute(select(Work).where(Work.tenant_id == tid).order_by(Work.ma_cong_trinh))).scalars())
        if ws:
            ct = []
            for w in ws:
                p = (await s.execute(select(WorkProgress).where(WorkProgress.work_id == w.id, WorkProgress.ngay <= end,
                                                                WorkProgress.trang_thai_xac_nhan == "da_xac_nhan")
                                     .order_by(WorkProgress.ngay.desc(), WorkProgress.id.desc()).limit(1))).scalar()
                ct.append({"ten": w.ten, "loai": ten.get(w.loai, w.loai), "trang_thai": w.trang_thai,
                           "ke_hoach_pct": _f(p.ke_hoach_pct) if p else None, "thuc_te_pct": _f(p.thuc_te_pct) if p else None,
                           "ngay": p.ngay if p else None, "ngay_ht": getattr(w, "ngay_ht", None), "lat": _f(w.lat), "lng": _f(w.lng)})
            loai: dict[str, int] = {}
            for c in ct:
                loai[c["loai"]] = loai.get(c["loai"], 0) + 1
            out["cong_trinh"] = {"so_cong_trinh": len(ct), "cong_trinh": ct, "theo_loai": [{"ten": k, "so": v} for k, v in loai.items()],
                                 "dung_tien_do": sum(1 for c in ct if c["thuc_te_pct"] is not None and c["thuc_te_pct"] >= (c["ke_hoach_pct"] or 0)),
                                 "cham": sum(1 for c in ct if c["thuc_te_pct"] is not None and c["thuc_te_pct"] < (c["ke_hoach_pct"] or 0)),
                                 "is_sample": any(w.is_sample for w in ws)}
    if "dan_cu" in chon:
        pop = await population(s, tid, km, False)
        if pop.get("tong_dan_so"):
            out["dan_cu"] = {"ky": pop["ky"], "tong_dan_so": _f(pop["tong_dan_so"]), "nam": _f(pop["nam"]), "nu": _f(pop["nu"]), "so_ho": _f(pop["so_ho"]),
                             "thap_tuoi": [{"nhom_tuoi": x["nhom_tuoi"], "nam": None if x["nam_an"] else _f(x["nam"]), "nu": None if x["nu_an"] else _f(x["nu"])}
                                           for x in pop["thap_tuoi"]],
                             "bien_dong": [{k: _f(v) if k != "ky" else v for k, v in x.items()} for x in pop.get("bien_dong") or []]}
    return out


async def _chi_dao(s: AsyncSession, tid: int, end: date, ten: dict) -> dict | None:
    """Chỉ đạo – điều hành: CHỈ số lượng tổng hợp (không nội dung, không người phụ trách)."""
    from app.alerts.models import Alert, FollowUpCase
    from app.catalog.models import Program

    alerts = list((await s.execute(select(Alert).where(Alert.tenant_id == tid, Alert.trang_thai != "het_hieu_luc"))).scalars())
    cases = list((await s.execute(select(FollowUpCase).where(FollowUpCase.tenant_id == tid))).scalars())
    progs = list((await s.execute(select(Program).where(Program.tenant_id == tid).order_by(Program.ma))).scalars())
    if not alerts and not progs:
        return None
    today = date.today()  # trạng thái hồ sơ là hiện tại nên quá hạn tính theo ngày hôm nay
    overdue = lambda c: c.trang_thai != "hoan_thanh" and c.han < today  # noqa: E731
    by_status = {k: 0 for k in TRANG_THAI_VAN_DE}
    for a in alerts:
        by_status[a.trang_thai] = by_status.get(a.trang_thai, 0) + 1
    lv: dict[str, int] = {}
    md: dict[str, int] = {}
    for a in alerts:
        lv[a.nhom] = lv.get(a.nhom, 0) + 1
        md[a.muc_do] = md.get(a.muc_do, 0) + 1
    dv: dict[str, dict] = {}
    for c in cases:
        d = dv.setdefault(c.co_quan_xu_ly or "Chưa phân công", {"ten": c.co_quan_xu_ly or "Chưa phân công", "hoan_thanh": 0, "dang_xu_ly": 0, "qua_han": 0})
        d["hoan_thanh" if c.trang_thai == "hoan_thanh" else ("qua_han" if overdue(c) else "dang_xu_ly")] += 1
    prog_out = []
    inds = {i.id: i for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tid))).scalars()}
    km = end.strftime("%Y-%m")
    for p in progs:
        if not p.indicator_ids:  # nhiệm vụ chưa gắn chỉ tiêu (mẫu chờ phường cung cấp) → không công khai
            continue
        pcts = []
        for iid in p.indicator_ids or []:
            if iid in inds:
                c = await card(s, inds[iid], km)
                if c["data_state"] == "da_xac_nhan" and c["hoan_thanh_pct"] is not None:
                    pcts.append(min(float(c["hoan_thanh_pct"]), 120.0))
        prog_out.append({"ten": p.ten, "don_vi": p.don_vi_chu_tri, "trang_thai": p.trang_thai,
                         "so_chi_tieu": len(p.indicator_ids or []), "tien_do_pct": round(sum(pcts) / len(pcts), 1) if pcts else None})
    return {
        "tong_van_de": len(alerts), "da_giao": len(cases), "hoan_thanh": sum(c.trang_thai == "hoan_thanh" for c in cases),
        "qua_han": sum(overdue(c) for c in cases),
        "theo_trang_thai": [{"ma": k, "ten": v, "so": by_status.get(k, 0)} for k, v in TRANG_THAI_VAN_DE.items()],
        "theo_linh_vuc": sorted([{"ten": TEN_PHAN_HE.get(k, k), "so": v} for k, v in lv.items()], key=lambda x: -x["so"]),
        "theo_muc_do": [{"ma": k, "ten": MUC_DO.get(k, k), "so": md.get(k, 0)} for k in MUC_DO],
        "theo_don_vi": sorted(dv.values(), key=lambda x: -(x["hoan_thanh"] + x["dang_xu_ly"] + x["qua_han"])),
        "nhiem_vu_trong_tam": prog_out, "is_sample": any(a.is_sample for a in alerts),
    }


def _phuc_vu(t: Tenant, km: str) -> dict | None:
    """Bộ chỉ số phục vụ người dân: kỳ gần nhất ≤ km do đơn vị nhập; kèm xu hướng tổng điểm."""
    data = (t.config or {}).get("chi_so_phuc_vu") or {}
    kys = sorted(k for k in data if k <= km)
    if not kys:
        return None
    cur = data[kys[-1]]
    tc = [{"ten": x["ten"], "diem": float(x["diem"]), "toi_da": float(x["toi_da"]),
           "ty_le_pct": round(float(x["diem"]) * 100 / float(x["toi_da"]), 1) if x["toi_da"] else None} for x in cur.get("tieu_chi", [])]
    return {"ky": kys[-1], "tong_diem": round(sum(x["diem"] for x in tc), 2), "toi_da": round(sum(x["toi_da"] for x in tc), 2),
            "xep_hang": cur.get("xep_hang"), "tong_don_vi": cur.get("tong_don_vi"), "tieu_chi": tc,
            "xu_huong": [{"ky": k, "tong_diem": round(sum(float(x["diem"]) for x in data[k].get("tieu_chi", [])), 2)} for k in kys[-12:]],
            "nguon": cur.get("nguon") or "Hệ thống đánh giá Bộ chỉ số phục vụ người dân, doanh nghiệp", "is_sample": bool(cur.get("minh_hoa"))}


async def _pakn_extra(s: AsyncSession, tid: int, d0: date, d1: date) -> dict:
    """Phân bố mức hài lòng và số phản ánh theo tổ dân phố (chỉ số đếm)."""
    from sqlalchemy import func

    from app.platform.models import ResidentialGroup
    from app.services_pakn.models import FeedbackTicket

    base = (FeedbackTicket.tenant_id == tid, FeedbackTicket.ngay_nhan >= d0, FeedbackTicket.ngay_nhan <= d1)
    hl = dict((await s.execute(select(FeedbackTicket.danh_gia_hai_long, func.count()).where(*base).group_by(FeedbackTicket.danh_gia_hai_long))).all())
    groups = {g.id: g.ten for g in (await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == tid))).scalars()}
    tdp = (await s.execute(select(FeedbackTicket.tdp_id, func.count()).where(*base, FeedbackTicket.tdp_id.is_not(None))
                           .group_by(FeedbackTicket.tdp_id))).all()
    return {
        "hai_long": [{"ma": k, "ten": v, "so": int(hl.get(k, 0))} for k, v in HAI_LONG.items()] + [{"ma": 0, "ten": "Chưa đánh giá", "so": int(hl.get(None, 0))}],
        "theo_tdp": sorted([{"ten": groups.get(i, f"Tổ {i}"), "so": int(n)} for i, n in tdp], key=lambda x: -x["so"]),
    }


def compare_row(t: Tenant, du_lieu: dict | None) -> dict:
    """Chỉ số so sánh giữa các phường từ bản công bố mới nhất (trang chung)."""
    d = du_lieu or {}
    cm = d.get("chuyen_muc") or {}
    ct = d.get("chi_tieu") or []
    return {
        "ten": t.ten, "slug": slug_of(t),
        "chi_tieu_dat_pct": round(sum(c["status"] == "dat" for c in ct) * 100 / len(ct), 1) if ct else None,
        "thu_ns_pct": (cm.get("ngan_sach") or {}).get("thu_dia_ban", {}).get("ty_le_pct"),
        "giai_ngan_pct": (cm.get("dau_tu_cong") or {}).get("ty_le_pct"),
        "tthc_dung_han_pct": ((cm.get("dich_vu_cong") or {}).get("tong") or {}).get("dung_han_pct"),
        "pakn_dung_han_pct": (cm.get("phan_anh") or {}).get("ty_le_dung_han_pct"),
        "dan_so": (cm.get("dan_cu") or {}).get("tong_dan_so"),
        "phuc_vu_diem": (cm.get("phuc_vu") or {}).get("tong_diem"),
    }


def ward_card(t: Tenant) -> dict:
    return {"id": t.id, "ten": t.ten, "cap": t.cap, "slug": slug_of(t), "ten_mien": domains_of(t), "ten_co_quan": agency_name(t),
            "logo_url": f"/api/files/{t.logo_key}" if t.logo_key else None}
