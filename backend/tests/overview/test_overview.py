from datetime import UTC, date, datetime
from decimal import Decimal as D

from app.core.db import admin_sessionmaker
from app.indicators.models import IndicatorValue
from app.platform.models import AdminUnitMapping, ResidentialGroup, Tenant
from app.population.models import PopulationStat
from seeds.run import seed_platform, seed_tenant
from tests.factories import bearer, login, make_tenant, make_user
from tests.indicators.helpers import add_value, make_indicator


async def _vy_token(client, username="chutich"):  # noqa: ANN001
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    r = await client.post("/api/auth/login", json={"username": username, "password": "Demo@2026"})
    return bearer(r.json()["access_token"])


async def test_overview_shape(client):
    h = await _vy_token(client)
    j = (await client.get("/api/overview", params={"ky": "2026-10"}, headers=h)).json()
    assert set(j) >= {"tenant", "co_du_lieu_minh_hoa", "modules", "the_chi_so", "nq01", "can_chi_dao", "xu_huong", "ban_do", "lich_cap_nhat", "do_day_du"}
    assert j["co_du_lieu_minh_hoa"] is True
    mas = [c["ma"] for c in j["the_chi_so"]]
    assert {"NS-THU-DB", "NS-THU-NSP", "DTC-GN", "DC-DAN-SO", "NQ01-10", "NQ01-12", "TTHC-DH", "PAKN-QH"} <= set(mas)
    tile = next(c for c in j["the_chi_so"] if c["ma"] == "NS-THU-DB")
    for k in ("ten", "thuc_hien", "don_vi", "ky", "status", "data_state", "nguon", "link"):
        assert k in tile
    assert j["nq01"]["tong"] == 23 and j["nq01"]["nguy_co"] >= 3
    assert j["can_chi_dao"] and len(j["ban_do"]["features"]) >= 5
    assert {r["nhom"] for r in j["lich_cap_nhat"]} >= {"ktxh", "ngan_sach", "dau_tu_cong", "cong_trinh", "tthc_pakn", "dan_cu", "gd_yt_mt"}


async def test_overview_filters_ky_tdp_donvi(client):
    h = await _vy_token(client)
    j9 = (await client.get("/api/overview", params={"ky": "2026-09"}, headers=h)).json()
    assert next(c for c in j9["the_chi_so"] if c["ma"] == "NS-THU-DB")["ky"] == "2026-09"
    all_pop = (await client.get("/api/overview", params={"ky": "2026-10"}, headers=h)).json()
    tdp = all_pop["bo_loc"]["tdp"][0]["id"]
    one = (await client.get("/api/overview", params={"ky": "2026-10", "tdp": tdp}, headers=h)).json()
    a = next(c for c in all_pop["the_chi_so"] if c["ma"] == "DC-DAN-SO")["thuc_hien"]
    b = next(c for c in one["the_chi_so"] if c["ma"] == "DC-DAN-SO")["thuc_hien"]
    assert b < a and "Tổ dân phố" in next(c for c in one["the_chi_so"] if c["ma"] == "DC-DAN-SO")["ten"]
    dv = (await client.get("/api/overview", params={"ky": "2026-10", "don_vi": "Phòng Văn hóa – Xã hội"}, headers=h)).json()
    assert dv["lich_cap_nhat"] and all(r["don_vi"] == "Phòng Văn hóa – Xã hội" for r in dv["lich_cap_nhat"] if r.get("don_vi"))


async def test_map_layer_permission(client):
    t = await make_tenant()
    u = await make_user(t, "nguoi_xem")
    h = bearer(await login(client, u["username"]))
    j = (await client.get("/api/overview", headers=h)).json()
    assert j["ban_do"]["lop"] == ["du_an", "cong_trinh"]  # người xem được xem lớp công trình/dự án công khai
    assert not any(c["ma"].startswith("NS-") for c in j["the_chi_so"])  # không có quyền đọc ngân sách


async def test_presentation_mode_hides_sensitive(client):
    h = await _vy_token(client)
    j = (await client.get("/api/overview", params={"ky": "2026-10", "che_do": "trinh_chieu"}, headers=h)).json()
    assert j["che_do"] == "trinh_chieu"
    for a in j["can_chi_dao"]:
        assert a["mo_ta"] == "" and a["ho_so"] is None
    assert not [c for c in j["the_chi_so"] if c.get("phan_loai_thong_tin") == "han_che"]


async def test_history_rollup_via_mapping(client):
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        s.add_all([AdminUnitMapping(tenant_id=t, ma_cu="XA-A", ten_cu="Xã A"), AdminUnitMapping(tenant_id=t, ma_cu="XA-B", ten_cu="Xã B")])
        await s.commit()
    cnt = await make_indicator(t, ma_chi_tieu="SO-HO-NGHEO", don_vi_do="hộ", chieu="theo_doi")
    pct = await make_indicator(t, ma_chi_tieu="TY-LE", don_vi_do="%", chieu="theo_doi")
    await add_value(t, cnt, "2026-10", 160)
    await add_value(t, pct, "2026-10", 98)
    async with admin_sessionmaker()() as s:
        for iid, a, b in ((cnt, 100, 50), (pct, 97, 95)):
            for ma, v in (("XA-A", a), ("XA-B", b)):
                s.add(IndicatorValue(indicator_id=iid, tenant_id=t, ky_bao_cao="2025-10", gia_tri=D(v), nguon="Báo cáo đơn vị cũ",
                                     don_vi_cung_cap=ma, thoi_diem_chot=datetime(2025, 11, 5, tzinfo=UTC), trang_thai="da_xac_nhan", dvhc_cu=ma))
        await s.commit()
    u = await make_user(t)
    h = bearer(await login(client, u["username"]))
    cards = {c["ma"]: c for c in (await client.get("/api/indicators", params={"ky": "2026-10"}, headers=h)).json()}
    assert cards["SO-HO-NGHEO"]["cung_ky"] == {"ky": "2025-10", "gia_tri": 150, "gop_tu": ["XA-A", "XA-B"]}
    assert cards["TY-LE"]["cung_ky"]["gia_tri"] is None  # tỷ lệ không được cộng gộp
    assert cards["SO-HO-NGHEO"]["thuc_hien"] == 160  # số của đơn vị cũ không lẫn vào kỳ hiện tại


async def test_tile_notes_use_vietnamese_number_format(client):
    h = await _vy_token(client)
    j = (await client.get("/api/overview", params={"ky": "2026-10"}, headers=h)).json()
    tile = next(c for c in j["the_chi_so"] if c["ma"] == "NS-THU-DB")
    assert tile["ghi_chu"] == "Dự toán năm 441 tỷ đồng"
