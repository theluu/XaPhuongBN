from decimal import Decimal

from app.catalog.models import Program


def program_progress(program: Program, statuses: dict[int, str]) -> dict:
    """Tổng hợp tiến độ nhiệm vụ trọng tâm từ trạng thái các chỉ tiêu thành phần."""
    counts = {"dat": 0, "nguy_co": 0, "chua_du_du_lieu": 0}
    for iid in program.indicator_ids:
        counts[statuses.get(iid, "chua_du_du_lieu")] += 1
    co_du_lieu = counts["dat"] + counts["nguy_co"]
    tong = len(program.indicator_ids)
    pct = (Decimal(counts["dat"]) * 100 / tong).quantize(Decimal("0.1")) if co_du_lieu else None
    return {"tong": len(program.indicator_ids), **counts, "ty_le_dat_pct": pct}
