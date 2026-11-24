"""Dải bản tin: thông báo hiệu lực theo ngày và đối tượng, tin vận hành tự sinh theo quyền, TV không có liên kết/đăng tin; liên kết nhanh."""
from datetime import date, timedelta

from seeds.run import seed_platform, seed_tenant
from tests.factories import bearer


async def _tok(client, u):  # noqa: ANN001
    r = await client.post("/api/auth/login", json={"username": u, "password": "Demo@2026"})
    return bearer(r.json()["access_token"])


async def test_ticker_items_audience_and_links(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    ct = await _tok(client, "chutich")
    j = (await client.get("/api/bang-tin", headers=ct)).json()
    titles = [x["tieu_de"] for x in j["muc"]]
    assert titles[0].startswith("Cảnh báo mưa lớn") or titles[0].startswith("Giao ban")  # khẩn/ghim chạy trước
    assert any(x["loai"] == "van_hanh" for x in j["muc"])  # tin vận hành tự sinh
    assert {"ten": "Cổng TTĐT phường Việt Yên", "url": "https://vietyen.bacninh.gov.vn"} in j["lien_ket"]
    assert j["co_quyen_dang"] is True
    # Đăng thông báo qua Quản lý dữ liệu; hết hiệu lực / không đúng đối tượng thì không hiện
    today = date.today()
    base = {"tieu_de": "Chỉ dành cho cán bộ nhập liệu", "muc_do": "thuong", "tu_ngay": today.isoformat(), "doi_tuong": ["nhap_lieu"], "hien_tren_tv": False}
    assert (await client.post("/api/du-lieu/thong_bao", json={"data": base}, headers=ct)).status_code == 201
    old = {**base, "tieu_de": "Đã hết hạn", "doi_tuong": [], "tu_ngay": (today - timedelta(days=9)).isoformat(), "den_ngay": (today - timedelta(days=1)).isoformat()}
    assert (await client.post("/api/du-lieu/thong_bao", json={"data": old}, headers=ct)).status_code == 201
    assert (await client.post("/api/du-lieu/thong_bao", json={"data": {**base, "doi_tuong": ["sai"]}}, headers=ct)).status_code == 422
    t_ct = [x["tieu_de"] for x in (await client.get("/api/bang-tin", headers=ct)).json()["muc"]]
    t_cb = [x["tieu_de"] for x in (await client.get("/api/bang-tin", headers=await _tok(client, "canbo1"))).json()["muc"]]
    assert "Chỉ dành cho cán bộ nhập liệu" in t_cb and "Chỉ dành cho cán bộ nhập liệu" not in t_ct
    assert "Đã hết hạn" not in t_ct
    tv = (await client.get("/api/bang-tin", headers=await _tok(client, "xem"))).json()
    assert tv["lien_ket"] == [] and tv["co_quyen_dang"] is False and "Chỉ dành cho cán bộ nhập liệu" not in [x["tieu_de"] for x in tv["muc"]]
    # Cán bộ nhập liệu không đăng được thông báo
    assert (await client.post("/api/du-lieu/thong_bao", json={"data": base}, headers=await _tok(client, "canbo1"))).status_code == 403


async def test_quick_links_config(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    qt = await _tok(client, "qtphuong")
    assert (await client.patch("/api/admin/tenant", json={"lien_ket": [{"ten": "X", "url": "javascript:alert(1)"}]}, headers=qt)).status_code == 422
    links = [{"ten": "Tra cứu hồ sơ", "url": "https://dichvucong.gov.vn/p/home/dvc-tra-cuu-ho-so.html"}, {"ten": "Phản ánh", "url": "/phan-anh"}]
    assert (await client.patch("/api/admin/tenant", json={"lien_ket": links}, headers=qt)).status_code == 200
    assert (await client.get("/api/bang-tin", headers=qt)).json()["lien_ket"] == links
