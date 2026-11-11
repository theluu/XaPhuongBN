from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.periods import parse_ky, prev
from app.platform.models import ResidentialGroup
from app.population.models import PopulationStat
from app.sources.registry import sink

NGUONG_AN = 5  # ô thống kê < 5 người bị ẩn để tránh nhận diện cá nhân
NHOM_TUOI = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59",
             "60-64", "65-69", "70-74", "75-79", "80-84", "85+"]


def _cell(v: Decimal | None) -> tuple[Decimal | None, bool]:
    if v is None:
        return None, False
    return (None, True) if v < NGUONG_AN else (v, False)


async def _rows(s: AsyncSession, tenant_id: int, ky: str) -> list[PopulationStat]:
    return list((await s.execute(select(PopulationStat).where(PopulationStat.tenant_id == tenant_id, PopulationStat.ky == ky))).scalars())


def _total(rows: list[PopulationStat]) -> Decimal | None:
    ward = [r for r in rows if r.tdp_id is None and r.chi_so == "nhan_khau"]
    detailed = [r for r in ward if r.gioi]
    if detailed:
        return sum((r.gia_tri for r in detailed), Decimal(0))
    return ward[0].gia_tri if ward else None


def _one(rows: list[PopulationStat], chi_so: str) -> Decimal | None:
    v = [r.gia_tri for r in rows if r.tdp_id is None and r.chi_so == chi_so]
    return sum(v, Decimal(0)) if v else None


async def population(s: AsyncSession, tenant_id: int, ky: str, allow_tdp: bool, months: int = 12) -> dict:
    rows = await _rows(s, tenant_id, ky)
    ward = [r for r in rows if r.tdp_id is None and r.chi_so == "nhan_khau" and r.gioi]
    by = defaultdict(lambda: {"nam": None, "nu": None})
    for r in ward:
        by[r.nhom_tuoi][r.gioi] = (by[r.nhom_tuoi][r.gioi] or 0) + r.gia_tri
    thap = []
    for nt in NHOM_TUOI:
        if nt in by:
            nam, nam_an = _cell(by[nt]["nam"])
            nu, nu_an = _cell(by[nt]["nu"])
            thap.append({"nhom_tuoi": nt, "nam": nam, "nu": nu, "nam_an": nam_an, "nu_an": nu_an})
    theo_tdp = None
    if allow_tdp:
        groups = {g.id: g for g in (await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == tenant_id).order_by(ResidentialGroup.ma_tdp))).scalars()}
        per = defaultdict(Decimal)
        for r in rows:
            if r.tdp_id and r.chi_so == "nhan_khau":
                per[r.tdp_id] += r.gia_tri
        theo_tdp = []
        for gid, g in groups.items():
            v, an = _cell(per.get(gid))
            theo_tdp.append({"tdp_id": gid, "ma_tdp": g.ma_tdp, "ten": g.ten, "nhan_khau": v, "an": an})
    bien_dong = []
    p = parse_ky(ky)
    for _ in range(months):
        rs = await _rows(s, tenant_id, str(p))
        if rs:
            bien_dong.append({"ky": str(p), "dan_so": _total(rs), **{k: _one(rs, k) for k in ("sinh", "tu", "chuyen_den", "chuyen_di")}})
        p = prev(p)
    nam = sum((r.gia_tri for r in ward if r.gioi == "nam"), Decimal(0)) if ward else None
    nu = sum((r.gia_tri for r in ward if r.gioi == "nu"), Decimal(0)) if ward else None
    return {"ky": ky, "tong_dan_so": _total(rows), "nam": nam, "nu": nu, "so_ho": _one(rows, "so_ho"), "thap_tuoi": thap,
            "theo_tdp": theo_tdp, "cho_phep_theo_tdp": allow_tdp, "bien_dong": list(reversed(bien_dong)),
            "nguong_an": NGUONG_AN, "is_sample": any(r.is_sample for r in rows)}


@sink("population")
async def population_sink(s: AsyncSession, tenant_id: int, records: list[dict]) -> int:
    n = 0
    for r in records:
        if r.get("chi_so") == "dan_so":
            s.add(PopulationStat(tenant_id=tenant_id, ky=r["ky"], chi_so="nhan_khau", gia_tri=Decimal(str(r["gia_tri"]))))
            n += 1
    await s.flush()
    return n
