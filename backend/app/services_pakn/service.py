from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.models import SharedCatalog
from app.services_pakn.models import AdminServiceStat, FeedbackTicket
from app.sources.registry import sink

DEFAULT_HAN = 10
OPEN = {"tiep_nhan", "dang_xu_ly", "qua_han"}


def add_working_days(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def working_days_between(a: date, b: date) -> int:
    """Số ngày làm việc từ a (không tính) đến b (tính). Âm nếu b < a."""
    if b < a:
        return -working_days_between(b, a)
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def _pct(a: int, b: int) -> Decimal | None:
    return (Decimal(a) * 100 / b).quantize(Decimal("0.1"), ROUND_HALF_UP) if b else None


async def deadlines(s: AsyncSession) -> dict[str, int]:
    rows = (await s.execute(select(SharedCatalog).where(SharedCatalog.loai == "loai_pakn"))).scalars()
    return {r.ma: int((r.thuoc_tinh or {}).get("han_xu_ly_ngay", DEFAULT_HAN)) for r in rows}


@sink("pakn")
async def pakn_sink(s: AsyncSession, tenant_id: int, records: list[dict]) -> int:
    """Ghi phản ánh từ API vào phân hệ; hạn xử lý tính theo quy định của từng loại việc (ngày làm việc)."""
    han = await deadlines(s)
    n = 0
    for r in records:
        nhan = date.fromisoformat(r["ngay_nhan"])
        days = han.get(r["loai_viec"], DEFAULT_HAN)
        row = (await s.execute(select(FeedbackTicket).where(FeedbackTicket.tenant_id == tenant_id, FeedbackTicket.ma == r["ma"]))).scalar()
        if row is None:
            row = FeedbackTicket(tenant_id=tenant_id, ma=r["ma"])
            s.add(row)
        row.loai_viec, row.linh_vuc, row.ngay_nhan = r["loai_viec"], r.get("linh_vuc", r["loai_viec"]), nhan
        row.so_ngay_quy_dinh, row.han_xu_ly = days, add_working_days(nhan, days)
        row.trang_thai = r["trang_thai"]
        row.trang_thai_tra_loi = r.get("trang_thai_tra_loi", "chua_tra_loi")
        row.danh_gia_hai_long = r.get("danh_gia_hai_long")
        row.tdp_id = r.get("tdp_id")
        row.is_sample = bool(r.get("is_sample", False))
        if r.get("ngay_hoan_thanh"):
            row.ngay_hoan_thanh = date.fromisoformat(r["ngay_hoan_thanh"])
        n += 1
    await s.flush()
    return n


async def due_soon(s: AsyncSession, tenant_id: int, today: date) -> list[dict]:
    """Phản ánh gần hạn (còn ≤ 20% thời hạn, tối thiểu 1 ngày làm việc) hoặc quá hạn."""
    out = []
    rows = (await s.execute(select(FeedbackTicket).where(FeedbackTicket.tenant_id == tenant_id, FeedbackTicket.trang_thai.in_(OPEN))
                            .order_by(FeedbackTicket.han_xu_ly))).scalars()
    for t in rows:
        con_lai = working_days_between(today, t.han_xu_ly)
        nguong = max(1, round(t.so_ngay_quy_dinh * 0.2))
        if today > t.han_xu_ly:
            muc = "qua_han"
        elif con_lai <= nguong:
            muc = "gan_han"
        else:
            continue
        out.append({"ma": t.ma, "loai_viec": t.loai_viec, "linh_vuc": t.linh_vuc, "ngay_nhan": t.ngay_nhan, "han_xu_ly": t.han_xu_ly,
                    "con_lai_ngay_lam_viec": con_lai, "muc": muc, "trang_thai": t.trang_thai})
    return out


def _bucket(d: date, group: str) -> str:
    if group == "ngay":
        return d.isoformat()
    if group == "tuan":
        y, w, _ = d.isocalendar()
        return f"{y}-W{w:02d}"
    return d.strftime("%Y-%m")


def _agg(rows: list[AdminServiceStat]) -> dict:
    t = {k: sum(getattr(r, k) for r in rows) for k in ("tiep_nhan", "giai_quyet", "dung_han", "qua_han", "truc_tuyen")}
    return {**t, "dung_han_pct": _pct(t["dung_han"], t["dung_han"] + t["qua_han"]), "truc_tuyen_pct": _pct(t["truc_tuyen"], t["tiep_nhan"]),
            "co_so_tam_thoi": any(r.trang_thai == "tam_thoi" for r in rows)}


async def tthc_summary(s: AsyncSession, tenant_id: int, tu: date, den: date, group: str, bo_phan: str | None) -> dict:
    q = select(AdminServiceStat).where(AdminServiceStat.tenant_id == tenant_id, AdminServiceStat.ngay >= tu, AdminServiceStat.ngay <= den)
    rows = list((await s.execute(q.order_by(AdminServiceStat.ngay))).scalars())
    sel = [r for r in rows if not bo_phan or r.bo_phan == bo_phan]
    by_k: dict[str, list] = defaultdict(list)
    for r in sel:
        by_k[_bucket(r.ngay, group)].append(r)
    by_bp: dict[str, list] = defaultdict(list)
    for r in rows:
        by_bp[r.bo_phan].append(r)
    return {"tong": _agg(sel), "theo_ky": [{"ky": k, **_agg(v)} for k, v in sorted(by_k.items())],
            "theo_bo_phan": [{"bo_phan": k, **_agg(v)} for k, v in sorted(by_bp.items())],
            "co_so_tam_thoi": any(r.trang_thai == "tam_thoi" for r in sel), "nguon": sorted({r.nguon for r in sel}),
            "is_sample": any(r.is_sample for r in sel)}


async def pakn_summary(s: AsyncSession, tenant_id: int, tu: date, den: date, today: date) -> dict:
    rows = list((await s.execute(select(FeedbackTicket).where(FeedbackTicket.tenant_id == tenant_id, FeedbackTicket.ngay_nhan >= tu,
                                                               FeedbackTicket.ngay_nhan <= den))).scalars())
    tt = {k: sum(1 for r in rows if r.trang_thai == k) for k in ("tiep_nhan", "dang_xu_ly", "hoan_thanh")}
    tt["qua_han"] = sum(1 for r in rows if r.trang_thai in OPEN and (r.trang_thai == "qua_han" or r.han_xu_ly < today))
    rated = [r.danh_gia_hai_long for r in rows if r.danh_gia_hai_long is not None]
    done = [r for r in rows if r.trang_thai == "hoan_thanh"]
    by_lv: dict[str, list] = defaultdict(list)
    for r in rows:
        by_lv[r.linh_vuc].append(r)
    return {
        "tong": len(rows), "theo_trang_thai": {k: tt[k] for k in ("tiep_nhan", "dang_xu_ly", "qua_han", "hoan_thanh")},
        "ty_le_da_tra_loi_pct": _pct(sum(r.trang_thai_tra_loi == "da_tra_loi" for r in rows), len(rows)),
        "ty_le_dung_han_pct": _pct(sum(1 for r in done if r.ngay_hoan_thanh is None or r.ngay_hoan_thanh <= r.han_xu_ly), len(done)),
        "hai_long_tb": (Decimal(sum(rated)) / len(rated)).quantize(Decimal("0.1"), ROUND_HALF_UP) if rated else None,
        "theo_linh_vuc": [{"linh_vuc": k, "tong": len(v), "qua_han": sum(1 for r in v if r.trang_thai in OPEN and r.han_xu_ly < today)}
                          for k, v in sorted(by_lv.items())],
        "is_sample": any(r.is_sample for r in rows),
    }
