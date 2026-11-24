"""DT V.2 lộ trình, V.3 tiêu chí nghiệm thu (chỉ tính dữ liệu thật), VI hồ sơ chuẩn bị."""
from datetime import date, timedelta

from seeds.run import purge_sample, seed_platform, seed_tenant
from tests.factories import bearer


async def _tok(client, username):  # noqa: ANN001
    r = await client.post("/api/auth/login", json={"username": username, "password": "Demo@2026"})
    return bearer(r.json()["access_token"])


async def test_pilot_page_roadmap_criteria_and_prep(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    h = await _tok(client, "qtphuong")
    j = (await client.get("/api/thi-diem", headers=h)).json()
    assert [g["ma"] for g in j["lo_trinh"]] == ["GD1", "GD2", "GD3", "GD4"]
    assert [(g["tu_ngay"], g["den_ngay"]) for g in j["lo_trinh"]] == [(1, 15), (16, 45), (46, 75), (76, 90)]
    assert [c["ma"] for c in j["tieu_chi"]] == ["TC1", "TC2", "TC3", "TC4", "TC5"]
    # Dữ liệu minh họa không được tính là kết quả nghiệm thu
    assert j["con_du_lieu_minh_hoa"] is True
    tc = {c["ma"]: c for c in j["tieu_chi"]}
    assert tc["TC1"]["ket_qua"] == "chua_dat" and tc["TC5"]["ket_qua"] == "chua_dat"
    assert any("minh họa" in x for x in tc["TC5"]["can_lam"])
    assert [x["ma"] for x in j["ho_so"]] == ["i", "ii", "iii", "iv", "v", "vi"]
    assert {"so_dang_nhap", "so_nguoi_dung_hoat_dong", "theo_vai_tro"} <= set(j["su_dung"])

    start = (date.today() - timedelta(days=20)).isoformat()
    r = await client.put("/api/thi-diem", headers=h, json={"bat_dau": start, "nguong_dung_han": 85, "viec": {"pham_vi": True},
                                                          "ho_so": {"i": {"trang_thai": "da_co", "ghi_chu": "Kế hoạch số 12/KH-UBND"}}})
    assert r.status_code == 200
    j = (await client.get("/api/thi-diem", headers=h)).json()
    assert j["ngay_thu"] == 21 and j["nguong_dung_han"] == 85
    assert next(g for g in j["lo_trinh"] if g["hien_tai"])["ma"] == "GD2"
    assert j["lo_trinh"][0]["viec"][0]["xong"] is True
    assert j["ho_so"][0] == {"ma": "i", "ten": j["ho_so"][0]["ten"], "trang_thai": "da_co", "ghi_chu": "Kế hoạch số 12/KH-UBND", "goi_y": j["ho_so"][0]["goi_y"]}
    assert (await client.put("/api/thi-diem", headers=h, json={"viec": {"khong_co": True}})).status_code == 422
    # Cán bộ nhập liệu không xem/sửa trang thí điểm
    assert (await client.get("/api/thi-diem", headers=await _tok(client, "canbo1"))).status_code == 403


async def test_criteria_count_only_real_data(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    await purge_sample("viet_yen")
    h = await _tok(client, "chutich")
    j = (await client.get("/api/thi-diem", headers=h)).json()
    assert j["con_du_lieu_minh_hoa"] is False
    tc = {c["ma"]: c for c in j["tieu_chi"]}
    assert tc["TC1"]["ket_qua"] == "chua_dat"  # chưa có dữ liệu thật
    assert tc["TC2"]["ket_qua"] == "chua_du_du_lieu"
