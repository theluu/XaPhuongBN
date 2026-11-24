"""Lịch nộp số, nhắc hạn và tỷ lệ nộp đúng hạn / chậm / thiếu (DT III.3, V.3)."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import Indicator
from app.core.periods import Period, prev
from app.indicators.models import IndicatorValue
from app.indicators.service import align

NHAC_TRUOC_NGAY = 3


def _pct(a: int, b: int) -> Decimal | None:
    return (Decimal(a) * 100 / b).quantize(Decimal("0.1"), ROUND_HALF_UP) if b else None


def _periods(loai: str, tu: date, den: date) -> list[Period]:
    p = align(Period(den.year, "thang", den.month), loai)
    while p.ket_thuc > den:
        p = prev(p)
    out = []
    while p.ket_thuc >= tu:
        out.append(p)
        p = prev(p)
    return out


async def _first_submit(s: AsyncSession, indicator_id: int, ky: str) -> date | None:
    d = (await s.execute(select(func.min(IndicatorValue.thoi_diem_dong_bo)).where(
        IndicatorValue.indicator_id == indicator_id, IndicatorValue.ky_bao_cao == ky, IndicatorValue.trang_thai != "tu_choi"))).scalar()
    return d.date() if d else None


async def submission_report(s: AsyncSession, tenant_id: int, tu: date, den: date, today: date) -> dict:
    from app.dau_moi.service import brief, lookup

    lk = await lookup(s, tenant_id)
    by_dm: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    ten_dm: dict[str, str] = {}
    inds = (await s.execute(select(Indicator).where(Indicator.tenant_id == tenant_id, Indicator.ky_cap_nhat.in_(["tuan", "thang", "quy", "nam"])))).scalars()
    count = defaultdict(int)
    by_dv: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    chi_tiet = []
    for ind in inds:
        for p in _periods(ind.ky_cap_nhat, tu, den):
            han = p.ket_thuc + timedelta(days=ind.han_cap_nhat_ngay)
            nop = await _first_submit(s, ind.id, str(p))
            if nop is not None:
                kq = "dung_han" if nop <= han else "cham"
            else:
                kq = "thieu" if today > han else "chua_den_han"
            count[kq] += 1
            by_dv[ind.don_vi_chu_quan][kq] += 1
            dms = lk.chi_tieu(ind.ma_chi_tieu, ind.nhom)
            for dm in dms:
                by_dm[dm.ma][kq] += 1
                ten_dm[dm.ma] = dm.ten
            if kq in ("cham", "thieu"):
                chi_tiet.append({"ma": ind.ma_chi_tieu, "ten": ind.ten, "ky": str(p), "han": han, "ngay_nop": nop, "ket_qua": kq,
                                 "don_vi": ind.don_vi_chu_quan, "dau_moi": brief(dms)})
    tong = count["dung_han"] + count["cham"] + count["thieu"]
    return {
        "tu": tu, "den": den, "tong": tong, "dung_han": count["dung_han"], "cham": count["cham"], "thieu": count["thieu"],
        "chua_den_han": count["chua_den_han"], "dung_han_pct": _pct(count["dung_han"], tong), "cham_pct": _pct(count["cham"], tong),
        "thieu_pct": _pct(count["thieu"], tong),
        "theo_don_vi": [{"don_vi": k, "dung_han": v["dung_han"], "cham": v["cham"], "thieu": v["thieu"],
                         "dung_han_pct": _pct(v["dung_han"], v["dung_han"] + v["cham"] + v["thieu"])} for k, v in sorted(by_dv.items())],
        "theo_dau_moi": [{"ma": k, "ten": ten_dm[k], "dung_han": v["dung_han"], "cham": v["cham"], "thieu": v["thieu"],
                          "dung_han_pct": _pct(v["dung_han"], v["dung_han"] + v["cham"] + v["thieu"])} for k, v in sorted(by_dm.items())],
        "chi_tiet": sorted(chi_tiet, key=lambda x: (x["ket_qua"] != "thieu", x["han"])),
    }


async def reminders(s: AsyncSession, tenant_id: int, today: date, groups: set[str] | None) -> list[dict]:
    """Nhắc nộp số: kỳ vừa kết thúc sắp đến hạn (≤ 3 ngày) hoặc đã quá hạn mà chưa có số.
    Mỗi mục ghi đầu mối chịu trách nhiệm cung cấp (DT V.1) để nhắc đúng cơ quan."""
    from app.dau_moi.service import brief, lookup

    lk = await lookup(s, tenant_id)
    q = select(Indicator).where(Indicator.tenant_id == tenant_id, Indicator.ky_cap_nhat.in_(["tuan", "thang", "quy", "nam"]))
    out = []
    for ind in (await s.execute(q.order_by(Indicator.ma_chi_tieu))).scalars():
        if groups is not None and "*" not in groups and ind.nhom not in groups:
            continue
        p = align(Period(today.year, "thang", today.month), ind.ky_cap_nhat)
        if p.ket_thuc >= today:
            p = prev(p)
        han = p.ket_thuc + timedelta(days=ind.han_cap_nhat_ngay)
        if await _first_submit(s, ind.id, str(p)):
            continue
        con_lai = (han - today).days
        if con_lai < 0:
            muc = "qua_han"
        elif con_lai <= NHAC_TRUOC_NGAY:
            muc = "sap_den_han"
        else:
            continue
        out.append({"ma": ind.ma_chi_tieu, "ten": ind.ten, "nhom": ind.nhom, "ky": str(p), "han": han, "con_lai_ngay": con_lai, "muc": muc,
                    "don_vi": ind.don_vi_chu_quan, "dau_moi": brief(lk.chi_tieu(ind.ma_chi_tieu, ind.nhom))})
    return sorted(out, key=lambda x: x["con_lai_ngay"])
