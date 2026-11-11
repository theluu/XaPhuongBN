from datetime import UTC, date, datetime
from decimal import Decimal as D

from sqlalchemy import update

from app.budget.models import BudgetLine
from app.compliance.service import reminders, submission_report
from app.core.db import admin_sessionmaker, tenant_session
from app.indicators.models import IndicatorValue
from tests.factories import bearer, login, make_tenant, make_user
from tests.indicators.helpers import add_value, make_indicator


async def _synced(vid: int, d: datetime) -> None:
    async with admin_sessionmaker()() as s:
        await s.execute(update(IndicatorValue).where(IndicatorValue.id == vid).values(thoi_diem_dong_bo=d))
        await s.commit()


async def test_compliance_rate():
    t = await make_tenant()
    a = await make_indicator(t, ky_cap_nhat="thang", han_cap_nhat_ngay=10, don_vi_chu_quan="Văn phòng")
    b = await make_indicator(t, ky_cap_nhat="thang", han_cap_nhat_ngay=10, don_vi_chu_quan="Địa chính")
    # tháng 8: a đúng hạn, b chậm; tháng 9: a đúng hạn, b thiếu; tháng 10: hạn 10/11 → tính đến 11/11 thì a thiếu, b đúng hạn
    await _synced(await add_value(t, a, "2026-08", 1), datetime(2026, 9, 5, tzinfo=UTC))
    await _synced(await add_value(t, b, "2026-08", 1), datetime(2026, 9, 20, tzinfo=UTC))
    await _synced(await add_value(t, a, "2026-09", 1), datetime(2026, 10, 8, tzinfo=UTC))
    await _synced(await add_value(t, b, "2026-10", 1), datetime(2026, 11, 3, tzinfo=UTC))
    async with tenant_session([t]) as s:
        r = await submission_report(s, t, date(2026, 8, 1), date(2026, 10, 31), date(2026, 11, 11))
    assert r["tong"] == 6
    assert (r["dung_han"], r["cham"], r["thieu"]) == (3, 1, 2)
    assert r["dung_han_pct"] == D("50.0") and r["thieu_pct"] == D("33.3")
    dv = {x["don_vi"]: x for x in r["theo_don_vi"]}
    assert (dv["Địa chính"]["cham"], dv["Địa chính"]["thieu"]) == (1, 1)


async def test_not_yet_due_is_not_counted():
    t = await make_tenant()
    await make_indicator(t, ky_cap_nhat="thang", han_cap_nhat_ngay=10)
    async with tenant_session([t]) as s:
        r = await submission_report(s, t, date(2026, 10, 1), date(2026, 10, 31), date(2026, 11, 5))
    assert r["tong"] == 0 and r["chua_den_han"] == 1 and r["dung_han_pct"] is None


async def test_reminder_before_deadline():
    t = await make_tenant()
    await make_indicator(t, ma_chi_tieu="NHAC-1", ky_cap_nhat="thang", han_cap_nhat_ngay=10, nhom="ktxh")
    await make_indicator(t, ma_chi_tieu="NHAC-2", ky_cap_nhat="thang", han_cap_nhat_ngay=10, nhom="gd_yt_mt", phan_he="gd_yt_mt")
    async with tenant_session([t]) as s:
        r = await reminders(s, t, date(2026, 11, 8), groups={"ktxh"})
        assert [(x["ma"], x["ky"], x["muc"]) for x in r] == [("NHAC-1", "2026-10", "sap_den_han")]
        assert r[0]["han"] == date(2026, 11, 10) and r[0]["con_lai_ngay"] == 2
        r = await reminders(s, t, date(2026, 11, 12), groups={"ktxh"})
        assert [(x["ma"], x["muc"]) for x in r] == [("NHAC-1", "qua_han")]
        assert await reminders(s, t, date(2026, 11, 2), groups={"ktxh"}) == []


async def _budget(t, nguon, v, ky="2026-10"):  # noqa: ANN001
    async with admin_sessionmaker()() as s:
        s.add(BudgetLine(tenant_id=t, nam=2026, ky=ky, loai="thu", nhom_ma="THUE_CTN", scope="dia_ban", du_toan=D(500), thuc_hien=D(v),
                         nguon_loai=nguon, trang_thai_doi_soat="cho_doi_soat", ngay_chot=datetime(2026, 11, 3, tzinfo=UTC)))
        await s.commit()


async def test_reconciliation_memo_required_when_diff(client):
    t = await make_tenant()
    await _budget(t, "bao_cao_chot", 100)
    await _budget(t, "api", 110)
    u = await make_user(t, "xac_nhan", nhom=["ngan_sach"])
    h = bearer(await login(client, u["username"]))
    r = await client.post("/api/budget/close", json={"ky": "2026-10"}, headers=h)
    assert r.status_code == 422
    assert r.json()["detail"]["thong_bao"] == "Còn chênh lệch chưa có biên bản giải trình"
    assert r.json()["detail"]["can_giai_trinh"][0]["ref"] == "thu/THUE_CTN/dia_ban"
    r = await client.post("/api/reconciliation", json={"doi_tuong": "ngan_sach", "ref": "thu/THUE_CTN/dia_ban", "ky": "2026-10",
                                                        "so_he_thong": 110, "so_ho_so": 100, "giai_trinh": " "}, headers=h)
    assert r.status_code == 422
    r = await client.post("/api/reconciliation", json={"doi_tuong": "ngan_sach", "ref": "thu/THUE_CTN/dia_ban", "ky": "2026-10",
                                                        "so_he_thong": 110, "so_ho_so": 100,
                                                        "giai_trinh": "Số API gồm khoản thu tạm nộp chưa hạch toán, Kho bạc xác nhận số chốt"}, headers=h)
    assert r.status_code == 201 and r.json()["chenh_lech"] == 10
    r = await client.post("/api/budget/close", json={"ky": "2026-10"}, headers=h)
    assert r.status_code == 200 and r.json()["so_dong_da_doi_soat"] == 2
    memos = (await client.get("/api/reconciliation", headers=h)).json()
    assert memos[0]["giai_trinh"].startswith("Số API")
