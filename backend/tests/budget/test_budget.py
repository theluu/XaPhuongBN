from datetime import UTC, date, datetime
from decimal import Decimal as D

from app.budget.models import BudgetLine
from app.budget.service import api_vs_closed, is_stale, overspend, revenue_risks
from app.core.db import admin_sessionmaker, tenant_session
from tests.factories import bearer, login, make_tenant, make_user


async def add(t, **kw):  # noqa: ANN001, ANN003
    base = dict(tenant_id=t, nam=2026, ky="2026-10", loai="thu", nhom_ma="THUE_CTN", scope="dia_ban", du_toan=D(100),
                nguon_loai="bao_cao_chot", trang_thai_doi_soat="da_doi_soat", ngay_chot=datetime(2026, 11, 3, tzinfo=UTC))
    base.update(kw)
    async with admin_sessionmaker()() as s:
        s.add(BudgetLine(**base))
        await s.commit()


async def _get(client, t, role="lanh_dao", **params):  # noqa: ANN001, ANN003
    u = await make_user(t, role)
    return await client.get("/api/budget/summary", params={"nam": 2026, "ky": "2026-10", **params},
                            headers=bearer(await login(client, u["username"])))


async def test_scopes_never_summed(client):
    t = await make_tenant()
    await add(t, scope="dia_ban", thuc_hien=D(100))
    await add(t, scope="ns_phuong", thuc_hien=D(30), du_toan=D(40))
    j = (await _get(client, t)).json()
    assert j["thu"]["dia_ban"]["thuc_hien"] == 100
    assert j["thu"]["ns_phuong"]["thuc_hien"] == 30
    assert set(j["thu"]) == {"dia_ban", "ns_phuong"}
    assert "tong" not in str(j["thu"])


async def test_budget_by_group_and_period(client):
    t = await make_tenant()
    await add(t, nhom_ma="THUE_CTN", du_toan=D(200), ke_hoach_ky=D(150), thuc_hien=D(160), uoc_th=D(210))
    await add(t, nhom_ma="LE_PHI", du_toan=D(50), ke_hoach_ky=D(40), thuc_hien=D(30))
    await add(t, ky="2026-09", nhom_ma="THUE_CTN", du_toan=D(200), thuc_hien=D(140))
    j = (await _get(client, t)).json()
    tot = j["thu"]["dia_ban"]
    assert tot == {"du_toan": 250, "ke_hoach_ky": 190, "thuc_hien": 190, "uoc_th": None, "ty_le_pct": 76.0}
    nh = {n["nhom_ma"]: n for n in j["nhom_thu"] if n["scope"] == "dia_ban"}
    assert nh["THUE_CTN"]["ty_le_pct"] == 80.0 and nh["THUE_CTN"]["ten"]
    assert nh["LE_PHI"]["nguy_co"] is True and nh["THUE_CTN"]["nguy_co"] is False


async def test_chi_by_nhiem_vu(client):
    t = await make_tenant()
    await add(t, loai="chi", scope="ns_phuong", nhom_ma="CHI_QLHC", nhiem_vu="NV_BMAY", du_toan=D(80), thuc_hien=D(60))
    await add(t, loai="chi", scope="ns_phuong", nhom_ma="CHI_SN_MT", nhiem_vu="NV_MOITRUONG", du_toan=D(20), thuc_hien=D(25))
    j = (await _get(client, t)).json()
    nv = {x["nhiem_vu"]: x for x in j["chi"]["theo_nhiem_vu"]}
    assert nv["NV_BMAY"]["thuc_hien"] == 60
    assert nv["NV_MOITRUONG"]["vuot_du_toan"] is True
    assert {x["nhom_ma"] for x in j["chi"]["theo_nhom"]} == {"CHI_QLHC", "CHI_SN_MT"}


async def test_missing_month_thuc_hien_is_null_not_zero(client):
    t = await make_tenant()
    await add(t, ky="2026-08", thuc_hien=D(70))
    await add(t, ky="2026-10", thuc_hien=D(90))
    j = (await _get(client, t)).json()
    trend = {x["ky"]: x for x in j["xu_huong_thang"]}
    assert trend["2026-09"]["thu_dia_ban"] is None
    assert trend["2026-08"]["thu_dia_ban"] == 70 and trend["2026-10"]["thu_dia_ban"] == 90


async def test_pending_reconciliation_flag(client):
    t = await make_tenant()
    await add(t, thuc_hien=D(10), trang_thai_doi_soat="cho_doi_soat")
    assert (await _get(client, t)).json()["cho_doi_soat"] is True


async def test_nguoi_xem_no_doc_ngan_sach(client):
    t = await make_tenant()
    assert (await _get(client, t, role="nguoi_xem")).status_code == 403


async def test_revenue_period_plan_alert():
    t = await make_tenant()
    await add(t, nhom_ma="THUE_CTN", ke_hoach_ky=D(150), thuc_hien=D(140))
    await add(t, nhom_ma="LE_PHI", ke_hoach_ky=None, thuc_hien=D(1))  # không có kế hoạch kỳ → không đánh giá
    await add(t, nhom_ma="THUE_TNCN", ke_hoach_ky=D(10), thuc_hien=D(12))
    async with tenant_session([t]) as s:
        r = await revenue_risks(s, t, 2026, "2026-10")
    assert [(x["nhom_ma"], x["scope"]) for x in r] == [("THUE_CTN", "dia_ban")]


async def test_budget_api_vs_closed_diff():
    t = await make_tenant()
    await add(t, nhom_ma="THUE_CTN", thuc_hien=D(100), nguon_loai="bao_cao_chot")
    await add(t, nhom_ma="THUE_CTN", thuc_hien=D(103), nguon_loai="api", trang_thai_doi_soat="cho_doi_soat")
    await add(t, nhom_ma="LE_PHI", thuc_hien=D(50), nguon_loai="bao_cao_chot")
    await add(t, nhom_ma="LE_PHI", thuc_hien=D(50.5), nguon_loai="api")
    async with tenant_session([t]) as s:
        r = await api_vs_closed(s, t, 2026, "2026-10", nguong_pct=D(2))
    assert [x["nhom_ma"] for x in r] == ["THUE_CTN"] and r[0]["chenh_pct"] == D("3.0")


async def test_official_value_prefers_closed_report(client):
    t = await make_tenant()
    await add(t, thuc_hien=D(100), nguon_loai="bao_cao_chot")
    await add(t, thuc_hien=D(103), nguon_loai="api")
    j = (await _get(client, t)).json()
    assert j["thu"]["dia_ban"]["thuc_hien"] == 100
    assert j["lech_api_chot"][0]["nhom_ma"] == "THUE_CTN"


async def test_chi_vuot_du_toan():
    t = await make_tenant()
    await add(t, loai="chi", scope="ns_phuong", nhom_ma="CHI_SN_MT", nhiem_vu="NV_MOITRUONG", du_toan=D(20), thuc_hien=D(25))
    await add(t, loai="chi", scope="ns_phuong", nhom_ma="CHI_QLHC", nhiem_vu="NV_BMAY", du_toan=D(80), thuc_hien=D(60))
    async with tenant_session([t]) as s:
        r = await overspend(s, t, 2026, "2026-10")
    assert [x["nhom_ma"] for x in r] == ["CHI_SN_MT"]


def test_budget_stale_alert():
    chot = datetime(2026, 10, 1, tzinfo=UTC)
    assert is_stale(chot, date(2026, 10, 20), "tuan") is True
    assert is_stale(chot, date(2026, 10, 6), "tuan") is False
    assert is_stale(chot, date(2026, 10, 25), "thang") is False
    assert is_stale(chot, date(2026, 11, 5), "thang") is True
    assert is_stale(None, date(2026, 11, 5), "thang") is True
