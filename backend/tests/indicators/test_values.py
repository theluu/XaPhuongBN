from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.db import tenant_session
from app.core.principal import CurrentUser
from app.indicators.service import completeness, create_value, source_diff
from tests.factories import bearer, login, make_tenant, make_user
from tests.indicators.helpers import add_plan, add_value, make_indicator


async def _cards(client, tok, **params):
    r = await client.get("/api/indicators", params=params, headers=bearer(tok))
    assert r.status_code == 200, r.text
    return {c["ma"]: c for c in r.json()}


async def test_cards_never_return_zero_for_missing(client):
    t = await make_tenant()
    iid = await make_indicator(t, ma_chi_tieu="THIEU-1")
    await add_plan(t, iid, "2026-10", 100)
    u = await make_user(t)
    c = (await _cards(client, await login(client, u["username"]), ky="2026-10"))["THIEU-1"]
    assert c["thuc_hien"] is None
    assert c["status"] == "chua_du_du_lieu"
    assert c["data_state"] == "chua_co_qua_han"
    assert c["ke_hoach"] == 100


async def test_card_has_full_provenance(client):
    t = await make_tenant()
    iid = await make_indicator(t, ma_chi_tieu="DU-1")
    await add_plan(t, iid, "2026-10", 100)
    await add_value(t, iid, "2026-10", 80, du_bao=95)
    await add_value(t, iid, "2026-09", 70)
    await add_value(t, iid, "2025-10", 60)
    u = await make_user(t)
    c = (await _cards(client, await login(client, u["username"]), ky="2026-10"))["DU-1"]
    assert c["thuc_hien"] == 80 and c["du_bao"] == 95
    assert c["status"] == "nguy_co" and c["hoan_thanh_pct"] == 80
    assert c["data_state"] == "da_xac_nhan"
    for k in ["nguon", "don_vi_cung_cap", "nguoi_xac_nhan", "thoi_diem_chot", "thoi_diem_dong_bo", "ky"]:
        assert k in c
    assert c["nguon"] == "Báo cáo UBND phường" and c["nguoi_xac_nhan"] == "Chủ tịch UBND"
    assert c["ky_truoc"] == {"ky": "2026-09", "gia_tri": 70}
    assert c["cung_ky"] == {"ky": "2025-10", "gia_tri": 60}


async def test_tam_thoi_shown_distinctly_and_pending_flag(client):
    t = await make_tenant()
    iid = await make_indicator(t, ma_chi_tieu="TT-1")
    await add_plan(t, iid, "2026-10", 100)
    await add_value(t, iid, "2026-10", 90, version=1)
    await add_value(t, iid, "2026-10", 101, trang_thai="tam_thoi", version=2)
    u = await make_user(t)
    c = (await _cards(client, await login(client, u["username"]), ky="2026-10"))["TT-1"]
    assert c["thuc_hien"] == 90 and c["data_state"] == "da_xac_nhan"
    assert c["co_so_moi_cho_xac_nhan"] is True
    t2 = await make_tenant()
    i2 = await make_indicator(t2, ma_chi_tieu="TT-2")
    await add_value(t2, i2, "2026-10", 50, trang_thai="tam_thoi")
    u2 = await make_user(t2)
    c2 = (await _cards(client, await login(client, u2["username"]), ky="2026-10"))["TT-2"]
    assert c2["thuc_hien"] == 50 and c2["data_state"] == "tam_thoi"


async def test_official_value_follows_priority(client):
    t = await make_tenant()
    iid = await make_indicator(t, ma_chi_tieu="UT-1", nguon_uu_tien=["chuyen_nganh", "phuong"])
    await add_value(t, iid, "2026-10", "98.1", nguon_loai="phuong")
    await add_value(t, iid, "2026-10", "97.4", nguon_loai="chuyen_nganh")
    u = await make_user(t)
    c = (await _cards(client, await login(client, u["username"]), ky="2026-10"))["UT-1"]
    assert c["thuc_hien"] == 97.4
    assert c["lech_nguon"] == {"phuong": 98.1, "chuyen_nganh": 97.4, "chenh": 0.7, "chenh_pct": 0.7}


async def test_source_diff_phuong_vs_chuyen_nganh():
    t = await make_tenant()
    iid = await make_indicator(t)
    await add_value(t, iid, "2026-10", "98.1", nguon_loai="phuong")
    await add_value(t, iid, "2026-10", "97.4", nguon_loai="chuyen_nganh")
    async with tenant_session([t]) as s:
        d = await source_diff(s, iid, "2026-10")
    assert d["chenh"] == Decimal("0.7")
    i2 = await make_indicator(t)
    await add_value(t, i2, "2026-10", "98.1", nguon_loai="phuong")
    async with tenant_session([t]) as s:
        assert await source_diff(s, i2, "2026-10") is None


async def test_completeness_score():
    t = await make_tenant()
    ids = [await make_indicator(t, nhom="gd_yt_mt", phan_he="gd_yt_mt") for _ in range(4)]
    await add_value(t, ids[0], "2026-10", 1)
    await add_value(t, ids[1], "2026-10", 1, trang_thai="tam_thoi")
    async with tenant_session([t]) as s:
        c = await completeness(s, t, "gd_yt_mt", "2026-10")
    assert c == {"du_kien": 4, "co_so": 2, "ty_le_pct": Decimal("50.0"), "da_xac_nhan_pct": Decimal("25.0")}


async def test_publish_rejects_value_without_provenance():
    t = await make_tenant()
    iid = await make_indicator(t)
    user = CurrentUser(id=1, tenant_id=t, tenant_ids=[t])
    async with tenant_session([t]) as s:
        with pytest.raises(HTTPException) as e:
            await create_value(s, user, iid, {"ky_bao_cao": "2026-10", "gia_tri": "5", "nguon": "", "don_vi_cung_cap": "X",
                                               "thoi_diem_chot": "2026-10-31T00:00:00Z"})
        assert e.value.status_code == 422
        assert e.value.detail == "Thiếu thông tin nguồn số liệu"


async def test_value_has_du_bao_field(client):
    t = await make_tenant()
    iid = await make_indicator(t, ma_chi_tieu="DB-1")
    await add_value(t, iid, "2026-10", None, du_bao=12)
    u = await make_user(t)
    c = (await _cards(client, await login(client, u["username"]), ky="2026-10"))["DB-1"]
    assert c["thuc_hien"] is None and c["du_bao"] == 12


async def test_value_null_stays_null():
    t = await make_tenant()
    iid = await make_indicator(t)
    vid = await add_value(t, iid, "2026-10", None)
    async with tenant_session([t]) as s:
        from app.indicators.models import IndicatorValue
        assert (await s.get(IndicatorValue, vid)).gia_tri is None


async def test_cross_tenant_get_returns_404(client):
    a, b = await make_tenant(), await make_tenant()
    ib = await make_indicator(b)
    vb = await add_value(b, ib, "2026-10", 5)
    ua = await make_user(a)
    tok = await login(client, ua["username"])
    r = await client.get(f"/api/indicators/values/{vb}", headers=bearer(tok))
    assert r.status_code == 404
    r = await client.get(f"/api/indicators/values/{vb}", params={"tenant": b}, headers=bearer(tok))
    assert r.status_code == 404


async def test_sensitive_group_hidden_without_permission(client):
    t = await make_tenant()
    await make_indicator(t, ma_chi_tieu="NS-1", nhom="ngan_sach", phan_he="ngan_sach")
    await make_indicator(t, ma_chi_tieu="KT-1")
    viewer = await make_user(t, "nguoi_xem")
    cards = await _cards(client, await login(client, viewer["username"]), ky="2026-10")
    assert "KT-1" in cards and "NS-1" not in cards


async def test_series_keeps_nulls(client):
    t = await make_tenant()
    iid = await make_indicator(t, ma_chi_tieu="SR-1")
    await add_value(t, iid, "2026-08", 5)
    await add_value(t, iid, "2026-10", 7)
    u = await make_user(t)
    r = await client.get("/api/indicators/SR-1/series", params={"tu": "2026-08", "den": "2026-10"},
                         headers=bearer(await login(client, u["username"])))
    assert [(x["ky"], x["gia_tri"]) for x in r.json()] == [("2026-08", 5), ("2026-09", None), ("2026-10", 7)]
