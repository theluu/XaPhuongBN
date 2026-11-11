"""Đánh giá trạng thái chỉ tiêu (DT II.1): đạt / có nguy cơ / chưa đủ dữ liệu.

Nguyên tắc:
- Mốc so sánh là kế hoạch của kỳ (DT IV.2); không tự lấy tỷ lệ số tháng đã qua.
- Không nội suy mục tiêu 2030 (Phụ lục 01).
- Thiếu số liệu → chưa đủ dữ liệu, không bao giờ coi là 0.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


@dataclass(frozen=True)
class Evaluation:
    status: str
    hoan_thanh_pct: Decimal | None
    muc_so_sanh: Decimal | None = None


MISSING = Evaluation("chua_du_du_lieu", None)


def _pct(a: Decimal, b: Decimal) -> Decimal | None:
    if b == 0:
        return None
    return (Decimal(a) * 100 / Decimal(b)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def evaluate(ind: Any, value: Decimal | None, plan: Decimal | None, nam: int | None = None) -> Evaluation:
    if value is None:
        return MISSING
    value = Decimal(value)
    if ind.chieu == "theo_doi":
        return Evaluation("theo_doi", None)
    if ind.chieu == "tang_tot":
        if plan is None:
            return MISSING
        return Evaluation("dat" if value >= plan else "nguy_co", _pct(value, plan), plan)
    if ind.chieu == "giam_tot":
        target = plan
        if target is None and ind.muc_tieu is not None and ind.han_muc_tieu_nam and nam and nam >= ind.han_muc_tieu_nam:
            target = Decimal(ind.muc_tieu)
        if target is None:
            return MISSING
        return Evaluation("dat" if value <= target else "nguy_co", None, target)
    # dat_nguong
    if plan is not None:
        return Evaluation("dat" if value >= plan else "nguy_co", _pct(value, plan), plan)
    if ind.muc_tieu_khoang:
        low = Decimal(ind.muc_tieu_khoang[0])
        return Evaluation("dat" if value >= low else "nguy_co", _pct(value, low), low)
    if ind.muc_tieu is None or ind.nguong_toan_tu is None:
        return MISSING
    target = Decimal(ind.muc_tieu)
    ok = value > target if ind.nguong_toan_tu == ">" else value >= target
    return Evaluation("dat" if ok else "nguy_co", _pct(value, target), target)
