"""Số liệu minh họa cho bộ chỉ tiêu (is_sample=True). Thiết kế có chủ đích để buổi demo có tình huống:
4 chỉ tiêu có nguy cơ (03b, 08a, 15, 16), 2 chỉ tiêu thiếu số (06, 09), 3 số tạm thời (13c, 14, 15 tháng 10),
1 cặp lệch nguồn (12: phường 99,1 – BHXH 98,6)."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.periods import parse_ky


def _months(y: int, a: int, b: int) -> list[str]:
    return [f"{y}-{m:02d}" for m in range(a, b + 1)]


def _ramp(keys: list[str], start: float, end: float) -> dict[str, float]:
    n = len(keys) - 1 or 1
    return {k: round(start + (end - start) * i / n, 1) for i, k in enumerate(keys)}


VALUES: dict[str, dict[str, float]] = {
    "NQ01-01a": {"2023": 91.2, "2024": 91.8, "2025": 92.3},
    "NQ01-01b": {"2023": 92.0, "2024": 92.6, "2025": 93.1},
    "NQ01-02": {"2023": 3.2, "2024": 3.5, "2025": 3.6},
    "NQ01-03a": {"2024": 100, "2025": 100},
    "NQ01-03b": {"2024": 80.0, "2025": 82.5},
    "NQ01-04": {"2024": 90.5, "2025": 91.0},
    "NQ01-05a": {"2025-Q1": 14.1, "2025-Q2": 15.0, "2025-Q3": 15.8, "2025-Q4": 16.4, "2026-Q1": 15.2, "2026-Q2": 15.9, "2026-Q3": 16.2},
    "NQ01-05b": {"2025-Q1": 11.8, "2025-Q2": 12.4, "2025-Q3": 12.9, "2025-Q4": 13.1, "2026-Q1": 12.1, "2026-Q2": 12.5, "2026-Q3": 12.6},
    "NQ01-07a": {"2024": 0, "2025": 0},
    "NQ01-07b": {"2024": 28, "2025": 32},
    "NQ01-08a": {"2024": 26.8, "2025": 27.4},
    "NQ01-08b": {"2024": 88, "2025": 91},
    "NQ01-10": {"2025-Q3": 61, "2025-Q4": 52, "2026-Q1": 49, "2026-Q2": 44, "2026-Q3": 38},
    "NQ01-11": {"2024": 66.7, "2025": 77.8},
    "NQ01-12": {"2025-10": 97.9, **_ramp(_months(2026, 1, 10), 98.2, 99.1)},
    "NQ01-13a": {"2025-Q3": 97.5, "2026-Q1": 98.2, "2026-Q2": 98.4, "2026-Q3": 98.6},
    "NQ01-13b": {"2025-Q3": 94.0, "2026-Q1": 95.5, "2026-Q2": 95.8, "2026-Q3": 96.0},
    "NQ01-13c": {"2025-Q3": 96.1, "2026-Q1": 96.8, "2026-Q2": 97.0, "2026-Q3": 97.2},
    "NQ01-14": {"2025-Q3": 98.1, "2026-Q1": 98.6, "2026-Q2": 98.9, "2026-Q3": 99.2},
    "NQ01-15": {"2025-10": 96.0, **_ramp(_months(2026, 1, 10), 96.4, 97.5)},
    "NQ01-16": {"2025-Q3": 8.1, "2026-Q1": 8.8, "2026-Q2": 9.2, "2026-Q3": 9.5},
    "DT-CX": {"2024": 6.9, "2025": 7.2},
    "DT-TRUONG": {"2024": 9, "2025": 9},
    "DT-LOP": {"2024": 228, "2025": 236},
    "DT-HS": {"2024": 8410, "2025": 8640},
}
CHUYEN_NGANH: dict[str, dict[str, float]] = {
    "NQ01-12": {"2025-10": 97.6, **_ramp(_months(2026, 1, 10), 97.9, 98.6)},
}
PLANS: dict[str, dict[str, float]] = {
    "NQ01-07a": {"2025": 0, "2026": 1},
    "NQ01-07b": {"2024": 28, "2025": 30, "2026": 35},
    "NQ01-08a": {"2024": 27, "2025": 28, "2026": 29},
    "NQ01-08b": {"2024": 88, "2025": 90, "2026": 92},
    "NQ01-09": {"2025": 72, "2026": 76},
    "NQ01-10": {"2025-Q3": 60, "2026-Q1": 50, "2026-Q2": 45, "2026-Q3": 40, "2026": 30, "2027": 0},
    "NQ01-11": {"2024": 66.7, "2025": 77.8, "2026": 77.8},
    "NQ01-12": {"2025": 97.8, "2026": 98.5},
    "NQ01-14": {"2025": 98.5, "2026": 99.0},
    "NQ01-15": {"2025": 96.5, "2026": 98.0},
    "NQ01-16": {"2025": 8.0, "2026": 10.0},
    "DT-CX": {"2024": 6.8, "2025": 7.0, "2026": 7.5},
}
TAM_THOI = {("NQ01-13c", "2026-Q3"), ("NQ01-14", "2026-Q3"), ("NQ01-15", "2026-10")}
CONFIRMER = {"ktxh": "Phó Chủ tịch UBND Hoàng Văn Đức", "dan_cu": "Phó Chủ tịch UBND Hoàng Văn Đức",
             "cong_trinh": "Phó Chủ tịch UBND Hoàng Văn Đức", "gd_yt_mt": "Phó Chủ tịch UBND Hoàng Văn Đức",
             "tthc_pakn": "Phó Chủ tịch UBND Hoàng Văn Đức", "ngan_sach": "Kế toán ngân sách Phạm Thu Dung"}


def _ten(s: str, p) -> str:  # noqa: ANN001
    for a, b in p.doi_ten.items():
        s = s.replace(a, b)
    return s


def _chot(ky: str) -> datetime:
    end = parse_ky(ky).ket_thuc
    return datetime(end.year, end.month, end.day, tzinfo=UTC) + timedelta(days=5)


def build(indicators: dict, tenant_id: int, nhap_id: int | None, xn_ids: dict[str, int]):  # noqa: ANN201
    from app.catalog.models import IndicatorPlan
    from app.indicators.models import IndicatorValue
    from seeds.sample.ho_so import P

    rows: list = []
    for ma, series in PLANS.items():
        ind = indicators[ma]
        for ky, v in series.items():
            rows.append(IndicatorPlan(indicator_id=ind.id, tenant_id=tenant_id, nam=int(ky[:4]), ky=ky,
                                      gia_tri_ke_hoach=Decimal(str(v)), can_cu="Kế hoạch phát triển KT-XH năm (minh họa)", is_sample=True))
    for src, data in (("phuong", VALUES | P.chi_tieu), ("chuyen_nganh", CHUYEN_NGANH)):
        for ma, series in data.items():
            ind = indicators[ma]
            for ky, v in series.items():
                tam = (ma, ky) in TAM_THOI and src == "phuong"
                rows.append(IndicatorValue(
                    indicator_id=ind.id, tenant_id=tenant_id, ky_bao_cao=ky, scope=ind.scope, gia_tri=Decimal(str(v)),
                    nguon_loai=src, nguon=ind.nguon_mac_dinh if src == "phuong" else "BHXH thành phố (đối soát)",
                    don_vi_cung_cap=ind.don_vi_chu_quan if src == "phuong" else "Bảo hiểm xã hội",
                    thoi_diem_chot=_chot(ky), trang_thai="tam_thoi" if tam else "da_xac_nhan",
                    nguoi_nhap_id=nhap_id, nguoi_xac_nhan_id=None if tam else xn_ids.get(ind.nhom),
                    nguoi_xac_nhan_ten=None if tam else P.chu(_ten(CONFIRMER.get(ind.nhom, "Chủ tịch UBND Lê Minh Châu"), P)),
                    ngay_xac_nhan=None if tam else _chot(ky) + timedelta(days=2), version=1, is_sample=True,
                ))
    return rows
