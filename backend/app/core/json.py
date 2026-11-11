from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.core.num import num


def jsonable(o: Any) -> Any:
    """Decimal → số (None giữ nguyên None)."""
    if isinstance(o, Decimal):
        return num(o)
    if isinstance(o, dict):
        return {k: jsonable(v) for k, v in o.items()}
    if isinstance(o, list | tuple):
        return [jsonable(v) for v in o]
    if isinstance(o, datetime | date):
        return o.isoformat()
    return o
