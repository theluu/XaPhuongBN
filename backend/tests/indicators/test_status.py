from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from app.core.periods import parse_ky, prev, same_period_last_year
from app.indicators.status import evaluate


def ind(chieu="tang_tot", toan_tu=None, muc_tieu=None, khoang=None, muc_tieu_2030=None, han=None):
    return SimpleNamespace(chieu=chieu, nguong_toan_tu=toan_tu, muc_tieu=muc_tieu, muc_tieu_khoang=khoang,
                           muc_tieu_2030=muc_tieu_2030, han_muc_tieu_nam=han)


@pytest.mark.parametrize("args,status,pct", [
    ((ind(), D(80), D(100)), "nguy_co", D("80.0")),
    ((ind(), D(100), D(100)), "dat", D("100.0")),
    ((ind(), D(120), D(100)), "dat", D("120.0")),
    ((ind("giam_tot"), D(0), D(0)), "dat", None),
    ((ind("giam_tot"), D(12), D(5)), "nguy_co", None),
    ((ind("giam_tot"), D(4), D(5)), "dat", None),
    ((ind(), None, D(100)), "chua_du_du_lieu", None),
    ((ind("dat_nguong", ">", D(90)), D(90), None), "nguy_co", D("100.0")),
    ((ind("dat_nguong", ">", D(90)), D("90.1"), None), "dat", D("100.1")),
    ((ind("dat_nguong", ">=", D("99.8")), D("99.8"), None), "dat", D("100.0")),
    ((ind("dat_nguong", khoang=[D(15), D(18)]), D("14.9"), None), "nguy_co", D("99.3")),
    ((ind("dat_nguong", khoang=[D(15), D(18)]), D(16), None), "dat", D("106.7")),
])
def test_evaluate(args, status, pct):
    e = evaluate(*args)
    assert e.status == status
    assert e.hoan_thanh_pct == pct


def test_no_interpolation_when_plan_missing():
    # Thu nhập: mục tiêu 2030 = 95 triệu; năm 2026 chưa có kế hoạch → không tự suy ra mục tiêu năm
    e = evaluate(ind("tang_tot", muc_tieu_2030=D(95)), D(80), None)
    assert e.status == "chua_du_du_lieu" and e.hoan_thanh_pct is None


def test_period_plan_overrides_threshold():
    # BHYT: ngưỡng 2030 là 99,8% nhưng kế hoạch năm 2026 giao 97%
    e = evaluate(ind("dat_nguong", ">=", D("99.8")), D("97.5"), D(97))
    assert e.status == "dat"


def test_giam_tot_uses_target_from_deadline_year():
    hn = ind("giam_tot", muc_tieu=D(0), han=2027)
    assert evaluate(hn, D(3), None, nam=2026).status == "chua_du_du_lieu"  # chưa có kế hoạch 2026
    assert evaluate(hn, D(3), None, nam=2027).status == "nguy_co"
    assert evaluate(hn, D(0), None, nam=2027).status == "dat"


def test_target_vs_actual_distinct():
    # mục tiêu không bao giờ được dùng làm giá trị thực hiện
    e = evaluate(ind("dat_nguong", ">=", D(100)), None, None)
    assert e.status == "chua_du_du_lieu"


def test_compare_prev_and_same_period():
    assert str(prev(parse_ky("2026-10"))) == "2026-09"
    assert str(prev(parse_ky("2026-01"))) == "2025-12"
    assert str(same_period_last_year(parse_ky("2026-10"))) == "2025-10"
    assert str(prev(parse_ky("2026-Q3"))) == "2026-Q2"
    assert str(prev(parse_ky("2026-Q1"))) == "2025-Q4"
    assert str(same_period_last_year(parse_ky("2026-Q3"))) == "2025-Q3"
    assert str(prev(parse_ky("2026"))) == "2025"
    assert str(prev(parse_ky("2026-W01"))) == "2025-W52"
    with pytest.raises(ValueError):
        parse_ky("2026-13")
