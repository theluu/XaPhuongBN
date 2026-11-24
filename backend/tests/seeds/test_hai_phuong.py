"""Bộ demo 2 phường (Việt Yên, Nếnh) trên cùng hệ thống: mỗi tài khoản chỉ thấy dữ liệu phường mình, số liệu khác nhau."""
from seeds.run import seed_platform, seed_tenant
from tests.factories import bearer


async def _tok(client, username):  # noqa: ANN001
    r = await client.post("/api/auth/login", json={"username": username, "password": "Demo@2026"})
    assert r.status_code == 200, r.text
    return bearer(r.json()["access_token"])


async def test_two_wards_see_only_their_own_data(client):
    await seed_platform()
    vy_id = await seed_tenant("viet_yen", with_sample=True)
    nenh_id = await seed_tenant("nenh", with_sample=True)
    assert vy_id != nenh_id
    vy, nenh = await _tok(client, "chutich"), await _tok(client, "nenh.chutich")

    me_vy = (await client.get("/api/auth/me", headers=vy)).json()
    me_nenh = (await client.get("/api/auth/me", headers=nenh)).json()
    assert me_vy["don_vi"] == "Phường Việt Yên" and me_nenh["don_vi"] == "Phường Nếnh"

    co_vy = (await client.get("/api/co-cau", headers=vy)).json()
    co_nenh = (await client.get("/api/co-cau", headers=nenh)).json()
    ten_vy = {x["ho_ten"] for x in co_vy["can_bo"]}
    ten_nenh = {x["ho_ten"] for x in co_nenh["can_bo"]}
    assert "Lê Minh Châu" in ten_vy and "Đào Thị Phương" in ten_nenh
    assert not ten_vy & ten_nenh

    pa_vy = (await client.get("/api/phan-anh", headers=vy)).json()
    pa_nenh = (await client.get("/api/phan-anh", headers=nenh)).json()
    items = lambda j: j["items"] if isinstance(j, dict) else j  # noqa: E731
    tieu_de_nenh = {x["tieu_de"] for x in items(pa_nenh)}
    assert "Nước thải từ khu công nghiệp chảy tràn ra mương tiêu" in tieu_de_nenh
    assert "Nước thải từ khu công nghiệp chảy tràn ra mương tiêu" not in {x["tieu_de"] for x in items(pa_vy)}
    lat_nenh = [float(x["lat"]) for x in items(pa_nenh) if x.get("lat") is not None]
    lat_vy = [float(x["lat"]) for x in items(pa_vy) if x.get("lat") is not None]
    assert lat_nenh and all(21.215 <= v <= 21.26 for v in lat_nenh)  # trong khung bản đồ của Nếnh
    assert sum(lat_nenh) / len(lat_nenh) < sum(lat_vy) / len(lat_vy) - 0.03  # nằm phía nam Việt Yên

    ov_vy = (await client.get("/api/dieu-hanh/tong-quan", headers=vy)).json()
    ov_nenh = (await client.get("/api/dieu-hanh/tong-quan", headers=nenh)).json()
    assert len(ov_nenh["bo_loc"]["tdp"]) == 9 and len(ov_vy["bo_loc"]["tdp"]) == 12
    ids_vy = {g["id"] for g in ov_vy["bo_loc"]["tdp"]}
    # Truy cập chéo bằng id của phường khác không trả về dữ liệu
    pa_id = items(pa_vy)[0]["id"]
    assert (await client.get(f"/api/phan-anh/{pa_id}", headers=nenh)).status_code == 404
    assert not ids_vy & {g["id"] for g in ov_nenh["bo_loc"]["tdp"]}
