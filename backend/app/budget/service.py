"""Thu – chi ngân sách (DT II.3). Nguyên tắc: không cộng gộp scope; thiếu số = None; so tiến độ với kế hoạch kỳ."""
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.budget.models import BudgetLine

Q = Decimal("0.1")


def _sum(vals: list[Decimal | None]) -> Decimal | None:
    """Tổng; nếu có bất kỳ phần nào thiếu thì trả None (không coi thiếu là 0)."""
    if not vals or any(v is None for v in vals):
        return None
    return sum(vals, Decimal(0))


def _pct(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None or not b:
        return None
    return (a * 100 / b).quantize(Q, ROUND_HALF_UP)


async def _lines(s: AsyncSession, tenant_id: int, nam: int, ky: str) -> list[BudgetLine]:
    rows = list((await s.execute(select(BudgetLine).where(
        BudgetLine.tenant_id == tenant_id, BudgetLine.nam == nam, BudgetLine.ky == ky))).scalars())
    # số chính thức: báo cáo đã chốt; nếu chưa có thì dùng số API (chờ đối soát)
    best: dict[tuple, BudgetLine] = {}
    for r in rows:
        k = (r.loai, r.nhom_ma, r.nhiem_vu, r.scope)
        if k not in best or (best[k].nguon_loai == "api" and r.nguon_loai == "bao_cao_chot"):
            best[k] = r
    return list(best.values())


def _totals(rows: list[BudgetLine]) -> dict:
    du_toan = _sum([r.du_toan for r in rows])
    th = _sum([r.thuc_hien for r in rows])
    return {"du_toan": du_toan, "ke_hoach_ky": _sum([r.ke_hoach_ky for r in rows]), "thuc_hien": th,
            "uoc_th": _sum([r.uoc_th for r in rows]), "ty_le_pct": _pct(th, du_toan)}


async def summary(s: AsyncSession, tenant_id: int, nam: int, ky: str, ten: dict[str, str]) -> dict:
    rows = await _lines(s, tenant_id, nam, ky)
    thu = [r for r in rows if r.loai == "thu"]
    chi = [r for r in rows if r.loai == "chi"]
    nhom_thu = [{
        "nhom_ma": r.nhom_ma, "ten": ten.get(r.nhom_ma, r.nhom_ma), "scope": r.scope, "du_toan": r.du_toan,
        "ke_hoach_ky": r.ke_hoach_ky, "thuc_hien": r.thuc_hien, "uoc_th": r.uoc_th, "ty_le_pct": _pct(r.thuc_hien, r.du_toan),
        "nguy_co": r.ke_hoach_ky is not None and r.thuc_hien is not None and r.thuc_hien < r.ke_hoach_ky,
        "trang_thai_doi_soat": r.trang_thai_doi_soat, "nguon_loai": r.nguon_loai,
    } for r in sorted(thu, key=lambda r: (r.scope, r.nhom_ma))]

    def group(key: str) -> list[dict]:
        g: dict[str, list[BudgetLine]] = defaultdict(list)
        for r in chi:
            g[getattr(r, key) or "khac"].append(r)
        out = []
        for k, rs in sorted(g.items()):
            t = _totals(rs)
            out.append({key: k, "ten": ten.get(k, k), **t,
                        "vuot_du_toan": t["thuc_hien"] is not None and t["du_toan"] is not None and t["thuc_hien"] > t["du_toan"]})
        return out

    m = int(ky[5:7])
    trend = []
    for mm in range(1, m + 1):
        k = f"{nam}-{mm:02d}"
        rs = await _lines(s, tenant_id, nam, k)
        trend.append({
            "ky": k,
            "thu_dia_ban": _sum([r.thuc_hien for r in rs if r.loai == "thu" and r.scope == "dia_ban"]) if any(r.loai == "thu" and r.scope == "dia_ban" for r in rs) else None,
            "thu_ns_phuong": _sum([r.thuc_hien for r in rs if r.loai == "thu" and r.scope == "ns_phuong"]) if any(r.loai == "thu" and r.scope == "ns_phuong" for r in rs) else None,
            "chi": _sum([r.thuc_hien for r in rs if r.loai == "chi"]) if any(r.loai == "chi" for r in rs) else None,
            "ke_hoach_thu_dia_ban": _sum([r.ke_hoach_ky for r in rs if r.loai == "thu" and r.scope == "dia_ban"]) if any(r.loai == "thu" and r.scope == "dia_ban" for r in rs) else None,
        })
    all_rows = list((await s.execute(select(BudgetLine).where(BudgetLine.tenant_id == tenant_id, BudgetLine.nam == nam, BudgetLine.ky == ky))).scalars())
    chots = [r.ngay_chot for r in all_rows if r.ngay_chot]
    return {
        "nam": nam, "ky": ky,
        "thu": {"dia_ban": _totals([r for r in thu if r.scope == "dia_ban"]), "ns_phuong": _totals([r for r in thu if r.scope == "ns_phuong"])},
        "chi": {"tong_hop": _totals(chi), "theo_nhom": group("nhom_ma"), "theo_nhiem_vu": group("nhiem_vu")},
        "nhom_thu": nhom_thu, "xu_huong_thang": trend,
        "cho_doi_soat": any(r.trang_thai_doi_soat == "cho_doi_soat" for r in rows),
        "lech_api_chot": await api_vs_closed(s, tenant_id, nam, ky),
        "ngay_chot_gan_nhat": max(chots) if chots else None,
        "co_du_lieu": bool(all_rows), "is_sample": any(r.is_sample for r in all_rows),
    }


async def revenue_risks(s: AsyncSession, tenant_id: int, nam: int, ky: str) -> list[dict]:
    """Khoản thu có nguy cơ không đạt theo tiến độ kỳ: chỉ xét khi có kế hoạch kỳ (DT II.3, IV.2)."""
    return [{"nhom_ma": r.nhom_ma, "scope": r.scope, "ke_hoach_ky": r.ke_hoach_ky, "thuc_hien": r.thuc_hien}
            for r in sorted(await _lines(s, tenant_id, nam, ky), key=lambda r: (r.scope, r.nhom_ma))
            if r.loai == "thu" and r.ke_hoach_ky is not None and r.thuc_hien is not None and r.thuc_hien < r.ke_hoach_ky]


async def api_vs_closed(s: AsyncSession, tenant_id: int, nam: int, ky: str, nguong_pct: Decimal = Decimal(2)) -> list[dict]:
    rows = list((await s.execute(select(BudgetLine).where(BudgetLine.tenant_id == tenant_id, BudgetLine.nam == nam, BudgetLine.ky == ky))).scalars())
    by: dict[tuple, dict[str, BudgetLine]] = defaultdict(dict)
    for r in rows:
        by[(r.loai, r.nhom_ma, r.nhiem_vu, r.scope)][r.nguon_loai] = r
    out = []
    for (loai, nhom, nv, scope), d in sorted(by.items(), key=lambda x: str(x[0])):
        a, c = d.get("api"), d.get("bao_cao_chot")
        if a and c and a.thuc_hien is not None and c.thuc_hien:
            pct = (abs(a.thuc_hien - c.thuc_hien) * 100 / c.thuc_hien).quantize(Q, ROUND_HALF_UP)
            if pct > nguong_pct:
                out.append({"loai": loai, "nhom_ma": nhom, "scope": scope, "api": a.thuc_hien, "bao_cao_chot": c.thuc_hien, "chenh_pct": pct})
    return out


async def overspend(s: AsyncSession, tenant_id: int, nam: int, ky: str) -> list[dict]:
    return [{"nhom_ma": r.nhom_ma, "nhiem_vu": r.nhiem_vu, "du_toan": r.du_toan, "thuc_hien": r.thuc_hien}
            for r in sorted(await _lines(s, tenant_id, nam, ky), key=lambda r: r.nhom_ma)
            if r.loai == "chi" and r.du_toan is not None and r.thuc_hien is not None and r.thuc_hien > r.du_toan]


CYCLE_DAYS = {"tuan": 7, "thang": 31}


def is_stale(last_chot: datetime | None, today: date, cycle: str = "thang", grace_days: int = 3) -> bool:
    if last_chot is None:
        return True
    return today > (last_chot.astimezone(UTC).date() + timedelta(days=CYCLE_DAYS[cycle] + grace_days))
