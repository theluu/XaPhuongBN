import pyotp
from sqlalchemy import func, select

from app.alerts.models import Alert
from app.core.db import admin_sessionmaker, tenant_session
from app.indicators.models import IndicatorValue
from seeds.run import seed_platform
from tests.factories import bearer, login, make_tenant, make_user, uid
from tests.indicators.helpers import add_plan, add_value, make_indicator


async def _platform_admin(client):  # noqa: ANN001
    await seed_platform()
    p = await make_tenant("Nền tảng", cap="nen_tang")
    u = await make_user(p, "quan_tri_nen_tang")
    return bearer(await login(client, u["username"]))


async def test_onboard_new_ward_end_to_end(client):
    h = await _platform_admin(client)
    ma = uid("P-DEMO2")
    body = {"ma_dvhc": ma, "ten": "Phường Demo 2", "cap": "phuong", "pack": "phuong_do_thi", "so_tdp": 6,
            "lanh_dao": {"username": uid("ct_demo2"), "ho_ten": "Nguyễn Văn Demo", "chuc_danh": "Chủ tịch UBND"}}
    r = await client.post("/api/platform/onboard", json=body, headers=h)
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["so_chi_tieu"] >= 23 and j["so_tdp"] == 6 and j["mat_khau_tam"]
    r = await client.post("/api/auth/login", json={"username": body["lanh_dao"]["username"], "password": j["mat_khau_tam"]})
    tok = bearer(r.json()["access_token"])
    me = (await client.get("/api/tenant", headers=tok)).json()
    assert me["ten"] == "Phường Demo 2" and me["ten_co_quan"][0] == "ĐẢNG ỦY – UBND PHƯỜNG DEMO 2"
    assert me["modules"]["ngan_sach"] == "dang_ket_noi"
    assert (await client.get("/api/sample-flag", headers=tok)).json() == {"co_du_lieu_minh_hoa": False}
    ov = (await client.get("/api/overview", headers=tok)).json()
    assert ov["nq01"]["tong"] == 23 and ov["nq01"]["chua_du_du_lieu"] == 23
    r = await client.post("/api/platform/onboard", json=body, headers=h)
    assert r.status_code == 409


async def test_onboard_requires_platform_admin(client):
    t = await make_tenant()
    u = await make_user(t, "quan_tri_don_vi")
    r = await client.post("/api/platform/onboard", json={"ma_dvhc": "X", "ten": "X", "cap": "phuong", "pack": "phuong_do_thi", "so_tdp": 1,
                                                          "lanh_dao": {"username": "x1", "ho_ten": "x", "chuc_danh": "x"}}, headers=bearer(await login(client, u["username"])))
    assert r.status_code == 403


async def _unit_admin(client, t=None):  # noqa: ANN001
    t = t or await make_tenant()
    u = await make_user(t, "quan_tri_don_vi")
    return t, bearer(await login(client, u["username"]))


async def test_create_user_and_totp(client):
    t, h = await _unit_admin(client)
    name = uid("pct")
    r = await client.post("/api/admin/users", json={"username": name, "ho_ten": "Phó Chủ tịch", "chuc_danh": "Phó Chủ tịch UBND", "don_vi": "UBND",
                                                     "role": "xac_nhan", "nhom": ["ktxh"]}, headers=h)
    assert r.status_code == 201
    uidn, pw = r.json()["id"], r.json()["mat_khau_tam"]
    r = await client.post(f"/api/admin/users/{uidn}/totp", headers=h)
    secret = r.json()["secret"]
    assert r.json()["otpauth_uri"].startswith("otpauth://totp/")
    from app.core.config import get_settings

    s = get_settings()
    s.REQUIRE_2FA = True
    try:
        assert (await client.post("/api/auth/login", json={"username": name, "password": pw})).status_code == 401
        assert (await client.post("/api/auth/login", json={"username": name, "password": pw, "otp": pyotp.TOTP(secret).now()})).status_code == 200
    finally:
        s.REQUIRE_2FA = False
    users = (await client.get("/api/admin/users", headers=h)).json()
    row = next(x for x in users if x["username"] == name)
    assert row["co_2fa"] is True and "totp_secret" not in row and "password_hash" not in row


async def test_plan_upsert_marks_custom(client):
    t, h = await _unit_admin(client)
    await make_indicator(t, ma_chi_tieu="KH-1")
    r = await client.put("/api/admin/indicators/KH-1/plans", json={"ky": "2026", "gia_tri": 98.5, "can_cu": "Nghị quyết HĐND phường"}, headers=h)
    assert r.status_code == 200
    r = await client.put("/api/admin/indicators/KH-1/plans", json={"ky": "2026", "gia_tri": 99, "can_cu": "Điều chỉnh"}, headers=h)
    plans = (await client.get("/api/admin/indicators/KH-1/plans", headers=h)).json()
    assert plans == [{"ky": "2026", "gia_tri": 99, "can_cu": "Điều chỉnh"}]


async def test_rule_toggle_disables_rule(client):
    t, h = await _unit_admin(client)
    i = await make_indicator(t)
    await add_plan(t, i, "2026-10", 100)
    await add_value(t, i, "2026-10", 50)
    rules = (await client.get("/api/admin/alert-rules", headers=h)).json()
    assert any(r["ma"] == "CT_CHAM_KH" and r["bat"] for r in rules) and all("can_cu" in r for r in rules)
    await client.put("/api/admin/alert-rules/CT_CHAM_KH", json={"bat": False}, headers=h)
    from app.alerts.engine import run_rules

    async with tenant_session([t]) as s:
        out = await run_rules(s, t, ky="2026-10")
        await s.commit()
    assert not [a for a in out if a.rule_ma == "CT_CHAM_KH"]


async def test_audit_viewer_only_own_tenant(client):
    t1, h1 = await _unit_admin(client)
    t2, h2 = await _unit_admin(client)
    await client.get("/api/auth/me", headers=h2)
    rows = (await client.get("/api/admin/audit", headers=h1)).json()
    assert rows and all(r["tenant_id"] == t1 for r in rows)


async def test_purge_sample_requires_confirmation(client):
    t, h = await _unit_admin(client)
    i = await make_indicator(t)
    await add_value(t, i, "2026-10", 1, is_sample=True)
    await add_value(t, i, "2026-09", 2)
    assert (await client.post("/api/admin/purge-sample", json={"xac_nhan": "xoa"}, headers=h)).status_code == 422
    r = await client.post("/api/admin/purge-sample", json={"xac_nhan": "XÓA DỮ LIỆU MINH HỌA"}, headers=h)
    assert r.status_code == 200 and r.json()["da_xoa"] >= 1
    async with admin_sessionmaker()() as s:
        assert (await s.execute(select(func.count()).select_from(IndicatorValue).where(IndicatorValue.tenant_id == t))).scalar() == 1


async def test_export_tenant_data_only_own(client):
    t1, h1 = await _unit_admin(client)
    t2, _ = await _unit_admin(client)
    await make_indicator(t1, ma_chi_tieu="EX-1")
    await make_indicator(t2, ma_chi_tieu="EX-2")
    r = await client.get("/api/admin/export", headers=h1)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    j = r.json()
    assert [i["ma_chi_tieu"] for i in j["indicator"]] == ["EX-1"]
    assert all("password_hash" not in u and "totp_secret" not in u for u in j["app_user"])
    assert "audit_log" not in j
