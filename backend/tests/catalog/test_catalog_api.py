from sqlalchemy import select

from app.catalog.models import Indicator, Program
from app.core.db import admin_sessionmaker
from tests.catalog.test_catalog import PACK
from app.catalog.packs import apply_pack
from tests.factories import bearer, login, make_tenant, make_user
from tests.indicators.helpers import add_plan, add_value


async def _setup():
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        await apply_pack(s, t, PACK)
        await s.commit()
        ids = {i.ma_chi_tieu: i.id for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == t))).scalars()}
    await add_plan(t, ids["P-01"], "2026-10", 100)
    await add_value(t, ids["P-01"], "2026-10", 120)
    return t


async def test_programs_with_progress(client):
    t = await _setup()
    u = await make_user(t, "lanh_dao")
    r = await client.get("/api/programs", params={"ky": "2026-10"}, headers=bearer(await login(client, u["username"])))
    assert r.status_code == 200
    p = r.json()[0]
    assert p["ma"] == "NV-1"
    assert p["tien_do"] == {"tong": 2, "dat": 1, "nguy_co": 0, "chua_du_du_lieu": 1, "ty_le_dat_pct": 50.0}
    assert [c["ma"] for c in p["chi_tieu"]] == ["P-01", "P-02"]


async def test_scenarios_list(client):
    t = await _setup()
    u = await make_user(t, "lanh_dao")
    r = await client.get("/api/scenarios", headers=bearer(await login(client, u["username"])))
    sc = r.json()[0]
    assert sc["ma"] == "KB-01" and sc["so_chi_tieu"] == 1 and sc["rule_codes"] == ["CT_CHAM_KH"]


async def test_program_hides_indicators_without_permission(client):
    t = await _setup()
    async with admin_sessionmaker()() as s:
        i = (await s.execute(select(Indicator).where(Indicator.tenant_id == t, Indicator.ma_chi_tieu == "P-02"))).scalar_one()
        i.nhom = "ngan_sach"
        await s.commit()
    v = await make_user(t, "nguoi_xem")
    p = (await client.get("/api/programs", params={"ky": "2026-10"}, headers=bearer(await login(client, v["username"])))).json()[0]
    assert [c["ma"] for c in p["chi_tieu"]] == ["P-01"]
