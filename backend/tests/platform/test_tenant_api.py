from sqlalchemy import select

from app.core.db import admin_sessionmaker
from app.platform.models import Tenant
from tests.factories import bearer, login, make_tenant, make_user


async def test_current_tenant_info(client):
    t = await make_tenant("Phường Hòa Bình")
    async with admin_sessionmaker()() as s:
        row = await s.get(Tenant, t)
        row.config = {"ten_co_quan": ["ĐẢNG ỦY – UBND PHƯỜNG HÒA BÌNH", "Hệ thống điều hành số phường"], "ban_do": {"tam": [21, 106], "zoom": 14}}
        await s.commit()
    u = await make_user(t, "nguoi_xem")
    r = await client.get("/api/tenant", headers=bearer(await login(client, u["username"])))
    assert r.status_code == 200
    j = r.json()
    assert j["ten"] == "Phường Hòa Bình"
    assert j["ten_co_quan"] == ["ĐẢNG ỦY – UBND PHƯỜNG HÒA BÌNH", "Hệ thống điều hành số phường"]
    assert j["logo_url"] is None
    assert j["ban_do"] == {"tam": [21, 106], "zoom": 14}
    assert set(j["modules"]) >= {"ktxh", "dan_cu", "ngan_sach"}


async def test_tenant_info_default_agency_name(client):
    t = await make_tenant("Xã An Lạc", cap="xa")
    u = await make_user(t, "lanh_dao")
    j = (await client.get("/api/tenant", headers=bearer(await login(client, u["username"])))).json()
    assert j["ten_co_quan"] == ["ỦY BAN NHÂN DÂN XÃ AN LẠC", "TRUNG TÂM ĐIỀU HÀNH THÔNG MINH"]


async def test_sample_flag(client):
    from tests.indicators.helpers import add_value, make_indicator

    t = await make_tenant()
    u = await make_user(t, "nguoi_xem")
    tok = await login(client, u["username"])
    assert (await client.get("/api/sample-flag", headers=bearer(tok))).json() == {"co_du_lieu_minh_hoa": False}
    iid = await make_indicator(t)
    await add_value(t, iid, "2026-10", 1, is_sample=True)
    assert (await client.get("/api/sample-flag", headers=bearer(tok))).json() == {"co_du_lieu_minh_hoa": True}
