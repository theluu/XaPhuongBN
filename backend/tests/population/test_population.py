from app.core.db import admin_sessionmaker
from app.platform.models import ResidentialGroup, Tenant
from app.population.models import PopulationStat
from tests.factories import bearer, login, make_tenant, make_user


async def _setup(allow_tdp=True):  # noqa: ANN001
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        (await s.get(Tenant, t)).config = {"cho_phep_theo_tdp": allow_tdp}
        g1 = ResidentialGroup(tenant_id=t, ma_tdp="TDP01", ten="Tổ dân phố số 1")
        g2 = ResidentialGroup(tenant_id=t, ma_tdp="TDP02", ten="Tổ dân phố số 2")
        s.add_all([g1, g2])
        await s.flush()
        rows = [
            ("2026-10", None, "nhan_khau", "nam", "0-4", 120), ("2026-10", None, "nhan_khau", "nu", "0-4", 115),
            ("2026-10", None, "nhan_khau", "nam", "85+", 4), ("2026-10", None, "nhan_khau", "nu", "85+", 9),
            ("2026-10", None, "so_ho", "", "", 70),
            ("2026-10", g1.id, "nhan_khau", "", "", 150), ("2026-10", g2.id, "nhan_khau", "", "", 3),
            ("2026-09", None, "nhan_khau", "nam", "0-4", 118), ("2026-09", None, "nhan_khau", "nu", "0-4", 110),
            ("2026-10", None, "sinh", "", "", 6), ("2026-10", None, "tu", "", "", 2),
            ("2026-10", None, "chuyen_den", "", "", 11), ("2026-10", None, "chuyen_di", "", "", 4),
        ]
        for ky, tdp, cs, gioi, nt, v in rows:
            s.add(PopulationStat(tenant_id=t, ky=ky, tdp_id=tdp, chi_so=cs, gioi=gioi, nhom_tuoi=nt, gia_tri=v))
        await s.commit()
        return t, g1.id, g2.id


async def _get(client, t, role="lanh_dao", **params):  # noqa: ANN001, ANN003
    u = await make_user(t, role)
    return await client.get("/api/population", params={"ky": "2026-10", **params}, headers=bearer(await login(client, u["username"])))


def test_population_has_no_pii_columns():
    cols = set(PopulationStat.__table__.c.keys())
    assert not cols & {"ho_ten", "cccd", "so_dinh_danh", "ngay_sinh", "dia_chi", "sdt"}


async def test_small_cell_suppressed(client):
    t, *_ = await _setup()
    j = (await _get(client, t)).json()
    cell = {x["nhom_tuoi"]: x for x in j["thap_tuoi"]}
    assert cell["85+"]["nam"] is None and cell["85+"]["nam_an"] is True
    assert cell["85+"]["nu"] == 9 and cell["0-4"]["nam"] == 120
    tdp = {x["ma_tdp"]: x for x in j["theo_tdp"]}
    assert tdp["TDP02"]["nhan_khau"] is None and tdp["TDP02"]["an"] is True and tdp["TDP01"]["nhan_khau"] == 150


async def test_totals_and_change(client):
    t, *_ = await _setup()
    j = (await _get(client, t)).json()
    assert j["tong_dan_so"] == 248 and j["nam"] == 124 and j["nu"] == 124 and j["so_ho"] == 70
    bd = {x["ky"]: x for x in j["bien_dong"]}
    assert bd["2026-10"] == {"ky": "2026-10", "dan_so": 248, "sinh": 6, "tu": 2, "chuyen_den": 11, "chuyen_di": 4}
    assert bd["2026-09"]["dan_so"] == 228 and bd["2026-09"]["sinh"] is None


async def test_tdp_breakdown_hidden_when_not_allowed(client):
    t, g1, _ = await _setup(allow_tdp=False)
    j = (await _get(client, t)).json()
    assert j["theo_tdp"] is None and j["cho_phep_theo_tdp"] is False
    r = await _get(client, t, tdp=g1)
    assert r.status_code == 403 and r.json()["detail"] == "Nguồn dữ liệu chưa cho phép thống kê theo tổ dân phố"


async def test_viewer_cannot_read_population(client):
    t, *_ = await _setup()
    assert (await _get(client, t, role="nguoi_xem")).status_code == 403
