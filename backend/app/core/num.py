from decimal import Decimal


def num(v: Decimal | int | float | None) -> float | None:
    """Số ra JSON. None giữ nguyên None — không bao giờ đổi thành 0."""
    if v is None:
        return None
    f = float(v)
    return int(f) if f.is_integer() else f
