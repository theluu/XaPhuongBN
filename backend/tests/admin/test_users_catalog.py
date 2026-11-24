from app.core.db import admin_sessionmaker
from app.auth.models import User
from tests.factories import PASSWORD, bearer, login, make_tenant, make_user


async def _admin(client):  # noqa: ANN001
    t = await make_tenant(cap="phuong")
    a = await make_user(t, "quan_tri_don_vi")
    return t, a, bearer(await login(client, a["username"]))


async def test_change_role_takes_effect_and_logs_out(client):
    t, a, h = await _admin(client)
    u = await make_user(t, "nguoi_xem")
    tok = bearer(await login(client, u["username"]))
    r = await client.patch(f"/api/admin/users/{u['id']}", json={"role": "nhap_lieu", "nhom": ["tthc_pakn"], "chuc_danh": "Chuyên viên"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["roles"] == ["nhap_lieu"] and r.json()["nhom"] == ["tthc_pakn"] and r.json()["chuc_danh"] == "Chuyên viên"
    assert (await client.get("/api/auth/me", headers=tok)).status_code == 401  # phiên cũ bị hủy
    assert (await client.patch(f"/api/admin/users/{u['id']}", json={"role": "nhap_lieu"}, headers=h)).status_code == 422  # thiếu nhóm
    assert (await client.patch(f"/api/admin/users/{a['id']}", json={"role": "nguoi_xem"}, headers=h)).status_code == 409


async def test_reset_unlock_restore(client):
    t, a, h = await _admin(client)
    u = await make_user(t, "nguoi_xem")
    r = await client.post(f"/api/admin/users/{u['id']}/reset-password", headers=h)
    pw = r.json()["mat_khau_tam"]
    assert (await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD})).status_code == 401
    assert (await client.post("/api/auth/login", json={"username": u["username"], "password": pw})).status_code == 200
    for _ in range(5):
        await client.post("/api/auth/login", json={"username": u["username"], "password": "sai"})
    assert (await client.post("/api/auth/login", json={"username": u["username"], "password": pw})).status_code == 423
    users = (await client.get("/api/admin/users", headers=h)).json()
    assert next(x for x in users if x["id"] == u["id"])["bi_khoa"] is True
    await client.post(f"/api/admin/users/{u['id']}/unlock", headers=h)
    assert (await client.post("/api/auth/login", json={"username": u["username"], "password": pw})).status_code == 200
    await client.post(f"/api/users/{u['id']}/revoke", json={"ly_do": "Chuyển công tác"}, headers=h)
    r = await client.post(f"/api/admin/users/{u['id']}/restore", headers=h)
    assert r.status_code == 200
    async with admin_sessionmaker()() as s:
        assert (await s.get(User, u["id"])).trang_thai == "hoat_dong"


async def test_other_unit_cannot_edit(client):
    t, a, h = await _admin(client)
    other = await make_tenant()
    u = await make_user(other, "nguoi_xem")
    assert (await client.patch(f"/api/admin/users/{u['id']}", json={"ho_ten": "X"}, headers=h)).status_code == 404


async def test_role_matrix(client):
    t, a, h = await _admin(client)
    m = (await client.get("/api/admin/roles", headers=h)).json()
    ld = next(r for r in m["vai_tro"] if r["ma"] == "lanh_dao")
    assert ld["quyen"]["canh_bao"] == ["doc", "duyet", "nhap"] and ld["quyen"]["ngan_sach"] == ["doc"] and ld["can_2fa"]
    tv = next(r for r in m["vai_tro"] if r["ma"] == "man_hinh_tv")
    assert tv["quyen"]["ngan_sach"] == [] and tv["quyen"]["tthc_pakn"] == ["doc"]


async def test_residential_groups_and_catalogs(client):
    t, a, h = await _admin(client)
    r = await client.post("/api/admin/dia-ban", json={"ma_tdp": "TDP01", "ten": "Tổ dân phố Đông", "loai": "tdp", "nguoi_dung_dau": "Ông Tổ trưởng",
                                                     "lat": 21.27, "lng": 106.1}, headers=h)
    assert r.status_code == 201, r.text
    gid = r.json()["id"]
    assert (await client.post("/api/admin/dia-ban", json={"ma_tdp": "TDP01", "ten": "Trùng"}, headers=h)).status_code == 409
    r = await client.put(f"/api/admin/dia-ban/{gid}", json={"ma_tdp": "TDP01", "ten": "Tổ dân phố Đông", "ngung_hoat_dong": True}, headers=h)
    assert r.json()["ngung_hoat_dong"] is True
    cat = (await client.get("/api/dieu-hanh/danh-muc", headers=h)).json()
    assert cat["dia_ban"] == []  # tổ đã ngừng hoạt động (sau sáp nhập) không còn trong biểu mẫu
    pb = cat["phong_ban"] + [{"ma": "TTYT", "ten": "Trạm Y tế phường", "loai": "phoi_hop"}]
    r = await client.put("/api/admin/danh-muc/phong-ban", json={"items": pb}, headers=h)
    assert r.status_code == 200
    bad = [p for p in pb if p["ma"] != "KTHTDT"]
    assert (await client.put("/api/admin/danh-muc/phong-ban", json={"items": bad}, headers=h)).status_code == 422  # đang chủ trì lĩnh vực
    lv = [{**x, "chu_tri": "TTYT"} if x["ma"] == "an_sinh" else x for x in cat["linh_vuc"]]
    assert (await client.put("/api/admin/danh-muc/linh-vuc", json={"items": lv}, headers=h)).status_code == 200
    assert (await client.put("/api/admin/danh-muc/linh-vuc", json={"items": [{"ma": "x", "ten": "X", "chu_tri": "KHONG"}]}, headers=h)).status_code == 422
    u = await make_user(t, "nhap_lieu", ["tthc_pakn"])
    assert (await client.put("/api/admin/danh-muc/linh-vuc", json={"items": lv}, headers=bearer(await login(client, u["username"])))).status_code == 403
