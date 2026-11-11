from decimal import Decimal


def vn(v: Decimal | float | int | None, digits: int = 2) -> str:
    """Định dạng số kiểu Việt Nam cho câu chữ cảnh báo."""
    if v is None:
        return "—"
    s = f"{float(v):,.{digits}f}".rstrip("0").rstrip(".") if digits else f"{float(v):,.0f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def money(v: Decimal | float | None) -> str:
    if v is None:
        return "—"
    f = float(v)
    if abs(f) >= 1e9:
        return f"{vn(f / 1e9, 1)} tỷ đồng"
    if abs(f) >= 1e6:
        return f"{vn(f / 1e6, 0)} triệu đồng"
    return f"{vn(f, 0)} đồng"
