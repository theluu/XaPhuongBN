"""Kỳ báo cáo: '2026' | '2026-Q3' | '2026-10' | '2026-W40'."""
import re
from dataclasses import dataclass
from datetime import date, timedelta


class KyError(ValueError):
    """Kỳ báo cáo không hợp lệ (trả 422 cho người dùng)."""


@dataclass(frozen=True, order=True)
class Period:
    nam: int
    loai: str  # nam | quy | thang | tuan
    so: int = 0

    def __str__(self) -> str:
        return {"nam": f"{self.nam}", "quy": f"{self.nam}-Q{self.so}", "thang": f"{self.nam}-{self.so:02d}",
                "tuan": f"{self.nam}-W{self.so:02d}"}[self.loai]

    @property
    def ket_thuc(self) -> date:
        if self.loai == "nam":
            return date(self.nam, 12, 31)
        if self.loai == "quy":
            m = self.so * 3
            return (date(self.nam + (m == 12), (m % 12) + 1, 1)) - timedelta(days=1)
        if self.loai == "thang":
            return date(self.nam + (self.so == 12), (self.so % 12) + 1, 1) - timedelta(days=1)
        return date.fromisocalendar(self.nam, self.so, 7)


def _weeks(y: int) -> int:
    return date(y, 12, 28).isocalendar()[1]


def parse_ky(s: str) -> Period:
    if m := re.fullmatch(r"(\d{4})", s):
        return Period(int(m[1]), "nam")
    if m := re.fullmatch(r"(\d{4})-Q([1-4])", s):
        return Period(int(m[1]), "quy", int(m[2]))
    if m := re.fullmatch(r"(\d{4})-(\d{2})", s):
        if 1 <= int(m[2]) <= 12:
            return Period(int(m[1]), "thang", int(m[2]))
    if m := re.fullmatch(r"(\d{4})-W(\d{2})", s):
        if 1 <= int(m[2]) <= _weeks(int(m[1])):
            return Period(int(m[1]), "tuan", int(m[2]))
    raise KyError(f"Kỳ báo cáo không hợp lệ: {s}")


def prev(p: Period) -> Period:
    if p.loai == "nam":
        return Period(p.nam - 1, "nam")
    if p.so > 1:
        return Period(p.nam, p.loai, p.so - 1)
    last = {"quy": 4, "thang": 12, "tuan": _weeks(p.nam - 1)}[p.loai]
    return Period(p.nam - 1, p.loai, last)


def same_period_last_year(p: Period) -> Period:
    if p.loai == "tuan":
        return Period(p.nam - 1, "tuan", min(p.so, _weeks(p.nam - 1)))
    return Period(p.nam - 1, p.loai, p.so)


def current(loai: str, today: date | None = None) -> Period:
    d = today or date.today()
    if loai == "nam":
        return Period(d.year, "nam")
    if loai == "quy":
        return Period(d.year, "quy", (d.month - 1) // 3 + 1)
    if loai == "tuan":
        y, w, _ = d.isocalendar()
        return Period(y, "tuan", w)
    return Period(d.year, "thang", d.month)
