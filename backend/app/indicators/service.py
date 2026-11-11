from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import Indicator, IndicatorPlan
from app.core.num import num
from app.core.periods import Period, parse_ky, prev, same_period_last_year
from app.core.principal import CurrentUser
from app.indicators.models import IndicatorValue
from app.indicators.status import evaluate

KY_LOAI = {"thang": "thang", "quy": "quy", "nam": "nam", "tuan": "tuan", "api": "thang", "ky_bao_cao": "thang"}


def align(p: Period, loai: str) -> Period:
    """Đưa kỳ yêu cầu về kỳ cập nhật của chỉ tiêu (VD tháng 10 → quý 4 / năm 2026)."""
    loai = KY_LOAI.get(loai, "thang")
    if p.loai == loai:
        return p
    d = p.ket_thuc
    if loai == "nam":
        return Period(d.year, "nam")
    if loai == "quy":
        return Period(d.year, "quy", (d.month - 1) // 3 + 1)
    if loai == "thang":
        return Period(d.year, "thang", d.month)
    y, w, _ = d.isocalendar()
    return Period(y, "tuan", w)


async def _rows(s: AsyncSession, indicator_id: int, ky: str, scope: str | None = None) -> list[IndicatorValue]:
    q = select(IndicatorValue).where(
        IndicatorValue.indicator_id == indicator_id, IndicatorValue.ky_bao_cao == ky, IndicatorValue.tdp_id.is_(None)
    )
    if scope:
        q = q.where(IndicatorValue.scope == scope)
    return list((await s.execute(q.order_by(IndicatorValue.version.desc(), IndicatorValue.id.desc()))).scalars())


def _resolve(ind: Indicator, rows: list[IndicatorValue]) -> tuple[IndicatorValue | None, str, bool]:
    """(giá trị hiển thị, data_state, có số mới chờ xác nhận)."""
    confirmed: dict[str, IndicatorValue] = {}
    for r in rows:
        if r.trang_thai == "da_xac_nhan" and r.nguon_loai not in confirmed:
            confirmed[r.nguon_loai] = r
    official = next((confirmed[n] for n in (ind.nguon_uu_tien or []) if n in confirmed), None)
    if official is None and confirmed:
        official = next(iter(confirmed.values()))
    pending = [r for r in rows if r.trang_thai == "tam_thoi"]
    if official is not None:
        newer = any(p.version > official.version and p.nguon_loai == official.nguon_loai for p in pending)
        return official, "da_xac_nhan", newer
    if pending:
        return pending[0], "tam_thoi", False
    return None, "chua_co_qua_han", False


def _diff(rows: list[IndicatorValue]) -> dict | None:
    by: dict[str, IndicatorValue] = {}
    for r in rows:
        if r.trang_thai != "tu_choi" and r.gia_tri is not None and r.nguon_loai not in by:
            by[r.nguon_loai] = r
    if "phuong" not in by or "chuyen_nganh" not in by:
        return None
    a, b = by["phuong"].gia_tri, by["chuyen_nganh"].gia_tri
    chenh = abs(a - b)
    if chenh == 0:
        return None
    pct = (chenh * 100 / abs(b)).quantize(Decimal("0.1"), ROUND_HALF_UP) if b else None
    return {"phuong": a, "chuyen_nganh": b, "chenh": chenh.normalize(), "chenh_pct": pct}


async def source_diff(s: AsyncSession, indicator_id: int, ky: str) -> dict | None:
    return _diff(await _rows(s, indicator_id, ky))


async def plan_for(s: AsyncSession, indicator_id: int, ky: str) -> Decimal | None:
    return (await s.execute(
        select(IndicatorPlan.gia_tri_ke_hoach).where(IndicatorPlan.indicator_id == indicator_id, IndicatorPlan.ky == ky)
    )).scalar()


async def _simple(s: AsyncSession, ind: Indicator, ky: str) -> float | None:
    v, _, _ = _resolve(ind, await _rows(s, ind.id, ky, ind.scope))
    return num(v.gia_tri) if v else None


async def card(s: AsyncSession, ind: Indicator, ky_req: str) -> dict:
    p = align(parse_ky(ky_req), ind.ky_cap_nhat)
    ky = str(p)
    rows = await _rows(s, ind.id, ky, ind.scope)
    v, state, newer = _resolve(ind, rows)
    plan = await plan_for(s, ind.id, ky)
    ev = evaluate(ind, v.gia_tri if v else None, plan, nam=p.nam)
    d = _diff(rows)
    kt, ck = prev(p), same_period_last_year(p)
    return {
        "id": ind.id, "ma": ind.ma_chi_tieu, "ten": ind.ten, "nhom": ind.nhom, "phan_he": ind.phan_he, "bo": ind.bo,
        "don_vi": ind.don_vi_do, "chieu": ind.chieu, "ky": ky,
        "ke_hoach": num(plan), "muc_tieu": num(ind.muc_tieu), "muc_tieu_khoang": [num(x) for x in ind.muc_tieu_khoang] if ind.muc_tieu_khoang else None,
        "nguong_toan_tu": ind.nguong_toan_tu, "muc_tieu_2030": num(ind.muc_tieu_2030), "muc_so_sanh": num(ev.muc_so_sanh),
        "thuc_hien": num(v.gia_tri) if v else None, "du_bao": num(v.du_bao) if v else None,
        "hoan_thanh_pct": num(ev.hoan_thanh_pct), "status": ev.status, "data_state": state,
        "ky_truoc": {"ky": str(kt), "gia_tri": await _simple(s, ind, str(kt))},
        "cung_ky": {"ky": str(ck), "gia_tri": await _simple(s, ind, str(ck))},
        "nguon": v.nguon if v else ind.nguon_mac_dinh, "nguon_loai": v.nguon_loai if v else None,
        "don_vi_cung_cap": v.don_vi_cung_cap if v else ind.don_vi_chu_quan,
        "nguoi_xac_nhan": v.nguoi_xac_nhan_ten if v else None,
        "thoi_diem_chot": v.thoi_diem_chot if v else None, "thoi_diem_dong_bo": v.thoi_diem_dong_bo if v else None,
        "lech_nguon": {k: num(x) for k, x in d.items()} if d else None,
        "co_so_moi_cho_xac_nhan": newer, "is_sample": bool(v and v.is_sample),
        "phan_loai_thong_tin": ind.phan_loai_thong_tin, "ky_cap_nhat": ind.ky_cap_nhat, "value_id": v.id if v else None,
    }


async def completeness(s: AsyncSession, tenant_id: int, nhom: str, ky_req: str) -> dict:
    inds = list((await s.execute(select(Indicator).where(Indicator.tenant_id == tenant_id, Indicator.nhom == nhom))).scalars())
    co_so = xac_nhan = 0
    for ind in inds:
        ky = str(align(parse_ky(ky_req), ind.ky_cap_nhat))
        rows = [r for r in await _rows(s, ind.id, ky) if r.trang_thai != "tu_choi" and r.gia_tri is not None]
        co_so += bool(rows)
        xac_nhan += any(r.trang_thai == "da_xac_nhan" for r in rows)
    n = len(inds)
    q = Decimal("0.1")
    return {
        "du_kien": n, "co_so": co_so,
        "ty_le_pct": (Decimal(co_so) * 100 / n).quantize(q) if n else None,
        "da_xac_nhan_pct": (Decimal(xac_nhan) * 100 / n).quantize(q) if n else None,
    }


REQUIRED = {"nguon": "nguồn", "don_vi_cung_cap": "đơn vị cung cấp", "thoi_diem_chot": "thời điểm chốt", "ky_bao_cao": "kỳ báo cáo"}


def _dec(v: object) -> Decimal | None:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return Decimal(str(v))
    except InvalidOperation as e:
        raise HTTPException(422, f"Giá trị không phải số: {v}") from e


async def create_value(s: AsyncSession, user: CurrentUser, indicator_id: int, data: dict) -> IndicatorValue:
    """Tạo số liệu mới ở trạng thái tạm thời. Bắt buộc đủ lý lịch nguồn (DT V.3)."""
    if any(not str(data.get(k) or "").strip() for k in REQUIRED):
        raise HTTPException(422, "Thiếu thông tin nguồn số liệu")
    ind = await s.get(Indicator, indicator_id)
    if ind is None:
        raise HTTPException(404, "Không tìm thấy chỉ tiêu")
    ky = str(parse_ky(data["ky_bao_cao"]))
    chot = data["thoi_diem_chot"]
    if isinstance(chot, str):
        chot = datetime.fromisoformat(chot.replace("Z", "+00:00"))
    elif isinstance(chot, date) and not isinstance(chot, datetime):
        chot = datetime(chot.year, chot.month, chot.day, tzinfo=UTC)
    nguon_loai = data.get("nguon_loai", "phuong")
    last = (await s.execute(
        select(IndicatorValue.version).where(
            IndicatorValue.indicator_id == indicator_id, IndicatorValue.ky_bao_cao == ky,
            IndicatorValue.nguon_loai == nguon_loai, IndicatorValue.tdp_id.is_(None),
        ).order_by(IndicatorValue.version.desc())
    )).scalar()
    row = IndicatorValue(
        indicator_id=indicator_id, tenant_id=ind.tenant_id, ky_bao_cao=ky, scope=data.get("scope") or ind.scope,
        gia_tri=_dec(data.get("gia_tri")), du_bao=_dec(data.get("du_bao")), nguon_loai=nguon_loai,
        source_id=data.get("source_id"), nguon=data["nguon"], don_vi_cung_cap=data["don_vi_cung_cap"],
        thoi_diem_chot=chot, trang_thai="tam_thoi", nguoi_nhap_id=user.id, ly_do=data.get("ly_do") or "",
        minh_chung_keys=data.get("minh_chung_keys") or [], version=(last or 0) + 1,
    )
    s.add(row)
    await s.flush()
    return row
