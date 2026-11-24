"""Quản trị nền tảng: quản lý đơn vị, tài khoản từng đơn vị, dữ liệu minh họa, tạm dừng và xóa đơn vị."""
from seeds.run import seed_platform
from tests.factories import PASSWORD, bearer, login, make_tenant, make_user, uid


async def _platform_admin(client):  # noqa: ANN001
    await seed_platform()
    p = await make_tenant("Nền tảng", cap="nen_tang")
    u = await make_user(p, "quan_tri_nen_tang")
    return bearer(await login(client, u["username"]))


async def _new_ward(client, h, ten="Phường Mẫu"):  # noqa: ANN001
    tinh = await make_tenant("Tỉnh Thử", cap="tinh")
    body = {"ma_dvhc": uid("P-M"), "ten": ten, "cap": "phuong", "parent_id": tinh, "pack": "phuong_do_thi", "so_tdp": 5, "tam": [21.18, 106.05],
            "lanh_dao": {"username": uid("ct"), "ho_ten": "Nguyễn Văn Mẫu", "chuc_danh": "Chủ tịch UBND"}}
    r = await client.post("/api/platform/onboard", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["tenant_id"], body


async def test_platform_manages_ward_info_and_accounts(client):
    h = await _platform_admin(client)
    tid, body = await _new_ward(client, h)
    t = (await client.get(f"/api/platform/tenants/{tid}", headers=h)).json()
    assert t["ban_do"]["tam"] == [21.18, 106.05] and t["so_nguoi_dung"] == 1 and t["ban_ghi_minh_hoa"] == 0

    r = await client.patch(f"/api/platform/tenants/{tid}", json={"ten": "Phường Mẫu Mới", "zoom": 15, "modules": {"ngan_sach": "tat"}}, headers=h)
    assert r.status_code == 200 and r.json()["ten"] == "Phường Mẫu Mới" and r.json()["ban_do"]["zoom"] == 15
    assert (await client.patch(f"/api/platform/tenants/{tid}", json={"tam": [48.8, 2.3]}, headers=h)).status_code == 422

    r = await client.post(f"/api/platform/tenants/{tid}/users", headers=h,
                          json={"username": uid("nl"), "ho_ten": "Cán bộ Nhập", "role": "nhap_lieu", "nhom": ["ktxh"]})
    assert r.status_code == 201 and r.json()["mat_khau_tam"]
    nid = r.json()["id"]
    assert (await client.post(f"/api/platform/tenants/{tid}/users", headers=h,
                              json={"username": uid("x"), "ho_ten": "X", "role": "quan_tri_nen_tang"})).status_code == 422
    r = await client.patch(f"/api/platform/tenants/{tid}/users/{nid}", json={"role": "xac_nhan", "nhom": ["ktxh", "dan_cu"]}, headers=h)
    assert r.json()["roles"] == ["xac_nhan"]
    assert (await client.delete(f"/api/platform/tenants/{tid}/users/{nid}", headers=h)).status_code == 409  # phải thu hồi trước
    assert (await client.patch(f"/api/platform/tenants/{tid}/users/{nid}", json={"trang_thai": "thu_hoi"}, headers=h)).status_code == 422
    r = await client.patch(f"/api/platform/tenants/{tid}/users/{nid}", json={"trang_thai": "thu_hoi", "ly_do": "Chuyển công tác"}, headers=h)
    assert r.json()["trang_thai"] == "thu_hoi"
    assert (await client.delete(f"/api/platform/tenants/{tid}/users/{nid}", headers=h)).status_code == 200
    users = (await client.get(f"/api/platform/tenants/{tid}/users", headers=h)).json()
    assert [u["username"] for u in users] == [body["lanh_dao"]["username"]]

    # Tài khoản của phường khác không sửa được qua đơn vị này
    other = await make_tenant("Phường Khác")
    ou = await make_user(other, "nhap_lieu", ["ktxh"])
    assert (await client.post(f"/api/platform/tenants/{tid}/users/{ou['id']}/reset-password", headers=h)).status_code == 404


async def test_platform_seeds_sample_for_new_ward_and_purges(client):
    h = await _platform_admin(client)
    tid, body = await _new_ward(client, h, "Phường Hòa Bình")
    r = await client.post(f"/api/platform/tenants/{tid}/du-lieu-minh-hoa", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["so_ban_ghi"] > 100 and r.json()["tai_khoan"]["chutich"] == body["lanh_dao"]["username"]
    t = (await client.get(f"/api/platform/tenants/{tid}", headers=h)).json()
    assert t["ban_ghi_minh_hoa"] > 100
    r = await client.delete(f"/api/platform/tenants/{tid}/du-lieu-minh-hoa", headers=h)
    assert r.json()["da_xoa"] > 100
    assert (await client.get(f"/api/platform/tenants/{tid}", headers=h)).json()["ban_ghi_minh_hoa"] == 0


async def test_suspend_blocks_login_and_delete_requires_code(client):
    h = await _platform_admin(client)
    t = await make_tenant("Phường Dừng")
    u = await make_user(t, "nhap_lieu", ["ktxh"])
    tok = bearer(await login(client, u["username"]))
    assert (await client.post(f"/api/platform/tenants/{t}/trang-thai", json={"trang_thai": "tam_dung"}, headers=h)).status_code == 422
    r = await client.post(f"/api/platform/tenants/{t}/trang-thai", json={"trang_thai": "tam_dung", "ly_do": "Sáp nhập"}, headers=h)
    assert r.status_code == 200
    assert (await client.get("/api/auth/me", headers=tok)).status_code == 401  # phiên cũ bị đăng xuất
    r = await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD})
    assert r.status_code == 403

    from app.core.db import admin_sessionmaker
    from app.platform.models import Tenant

    async with admin_sessionmaker()() as s:
        ma = (await s.get(Tenant, t)).ma_dvhc
    assert (await client.request("DELETE", f"/api/platform/tenants/{t}", json={"xac_nhan": "sai"}, headers=h)).status_code == 422
    r = await client.request("DELETE", f"/api/platform/tenants/{t}", json={"xac_nhan": ma}, headers=h)
    assert r.status_code == 200, r.text
    assert (await client.get(f"/api/platform/tenants/{t}", headers=h)).status_code == 404


async def test_ward_admin_cannot_use_platform_endpoints(client):
    t = await make_tenant()
    u = await make_user(t, "quan_tri_don_vi")
    h = bearer(await login(client, u["username"]))
    assert (await client.get(f"/api/platform/tenants/{t}/users", headers=h)).status_code == 403
    assert (await client.post(f"/api/platform/tenants/{t}/du-lieu-minh-hoa", headers=h)).status_code == 403


async def test_platform_admin_enters_ward_and_manages_all_content(client):
    from seeds.run import seed_tenant

    h = await _platform_admin(client)
    vy = await seed_tenant("viet_yen", with_sample=True)
    nenh = await seed_tenant("nenh", with_sample=True)
    r = await client.post(f"/api/platform/tenants/{nenh}/vao-quan-tri", headers=h)
    assert r.status_code == 200, r.text
    act = bearer(r.json()["access_token"])
    me = (await client.get("/api/auth/me", headers=act)).json()
    assert me["dai_dien"] is True and me["tenant_id"] == nenh and "quan_tri_don_vi" in me["roles"]
    assert (await client.get("/api/tenant", headers=act)).json()["ten"] == "Phường Nếnh"
    # Thấy và sửa được nội dung nghiệp vụ của Nếnh (kể cả nhóm nhạy cảm), không thấy Việt Yên
    pa = (await client.get("/api/phan-anh", headers=act)).json()
    items = pa["items"] if isinstance(pa, dict) else pa
    assert items and "Nước thải từ khu công nghiệp chảy tràn ra mương tiêu" in {x["tieu_de"] for x in items}
    users = (await client.get("/api/admin/users", headers=act)).json()
    assert {u["username"] for u in users} >= {"nenh.chutich", "nenh.canbo1"} and "chutich" not in {u["username"] for u in users}
    co = (await client.get("/api/co-cau", headers=act)).json()
    don_vi = next(u for u in co["don_vi"] if u["ma"] == "VP")
    r = await client.post("/api/co-cau/can-bo", headers=act, json={"ma": "BS01", "don_vi_ma": "VP", "ho_ten": "Cán bộ Bổ sung", "chuc_vu": "Chuyên viên", "cap": "thanh_vien"})
    assert r.status_code in (200, 201), r.text
    assert don_vi
    # Phiên đại diện không lồng nhau; tài khoản thường không dùng được
    assert (await client.post(f"/api/platform/tenants/{vy}/vao-quan-tri", headers=act)).status_code == 409
    t = await make_tenant()
    u = await make_user(t, "quan_tri_don_vi")
    assert (await client.post(f"/api/platform/tenants/{nenh}/vao-quan-tri", headers=bearer(await login(client, u["username"])))).status_code == 403
    # Tạm dừng đơn vị → phiên đại diện hết hiệu lực
    await client.post(f"/api/platform/tenants/{nenh}/trang-thai", json={"trang_thai": "tam_dung", "ly_do": "Thử"}, headers=h)
    assert (await client.get("/api/auth/me", headers=act)).status_code == 401
    await client.post(f"/api/platform/tenants/{nenh}/trang-thai", json={"trang_thai": "hoat_dong"}, headers=h)
