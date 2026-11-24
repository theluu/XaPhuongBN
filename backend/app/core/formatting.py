import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

EMPTY = {"", "-", "—", "–"}


def parse_vn_number(v: object) -> Decimal | None:
    """Đọc số theo thói quen nhập liệu Việt Nam. Ô trống / gạch ngang → None (không phải 0)."""
    if v is None:
        return None
    if isinstance(v, bool):
        raise ValueError("Không phải số")
    if isinstance(v, int | float | Decimal):
        d = Decimal(str(v))
        if not d.is_finite():
            raise ValueError(f"'{v}' không phải là số hợp lệ")
        return d
    s = str(v).strip().replace(" ", "").replace(" ", "")
    if s in EMPTY:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    if not re.fullmatch(r"-?\d+(\.\d+)?", s):
        raise ValueError(f"'{v}' không phải là số")
    try:
        return Decimal(s)
    except InvalidOperation as e:
        raise ValueError(f"'{v}' không phải là số") from e


def parse_vn_date(v: object) -> date | None:
    if v is None or (isinstance(v, str) and v.strip() in EMPTY):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"'{v}' không phải ngày hợp lệ (dd/mm/yyyy)")
