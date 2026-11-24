"""Đầu mối & trách nhiệm (DT V.1): danh mục mặc định đúng dự thảo, gắn tài khoản, nhắc đúng cơ quan, quyền sửa, cách ly đơn vị."""
from seeds.run import seed_platform, seed_tenant
from tests.factories import bearer, login, make_tenant, make_user


async def _tok(client, username):  # noqa: ANN001
    r = await client.post("/api/auth/login", json={"username": username, "password": "Demo@2026"})
    assert r.status_code == 200, r.text
    return bearer(r.json()["access_token"])


async def test_default_focal_points_follow_draft_v1(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    h = await _tok(client, "chutich")
    j = (await client.get("/api/dau-moi", headers=h)).json()
    by = {d["ma"]: d for d in j["dau_moi"]}
    # 6 đầu mối mục V.1 đều có
    for ma in ("UBND", "SOKHCN", "VPUBNDTP", "STC", "KBNN", "THUE", "CATP", "SXD", "BQLDA"):
        assert ma in by, ma
    assert by["UBND"]["ten"] == "UBND phường Việt Yên"
    assert {"nhom": "chung", "vai_tro": "chu_tri"}.items() <= by["SOKHCN"]["trach_nhiem"][0].items()
    assert any(t["nhom"] == "ngan_sach" and t["vai_tro"] == "chu_tri" for t in by["STC"]["trach_nhiem"])
    assert "KHO_DL_DAN_CU" in by["CATP"]["nguon"] and "NQ01-12" in by["BHXH"]["chi_tieu"]
    # Phụ lục 02: đủ 8 mục A–H được phân cho ít nhất một đầu mối
    assert {p["ma"] for d in j["dau_moi"] for p in d["phieu_nguon"]} == set("ABCDEFGH")
    # Tài khoản gắn với đầu mối
    assert {a["username"] for a in by["THUE"]["tai_khoan"]} == {"thue"}
    assert {"chutich", "xacnhan", "ketoan"} <= {a["username"] for a in by["UBND"]["tai_khoan"]}
    assert by["SOKHCN"]["tai_khoan"][0]["roles"] == ["quan_tri_nen_tang"]
    assert "UBND" in j["cua_toi"]


async def test_agency_account_scope_and_reminders_name_the_agency(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    h = await _tok(client, "thue")
    me = (await client.get("/api/auth/me", headers=h)).json()
    assert me["roles"] == ["chuyen_nganh"] and set(me["quyen"]) == {"ngan_sach"} and me["don_vi"] == "Cơ quan Thuế"
    assert (await client.get("/api/dau-moi", headers=h)).json()["cua_toi"] == ["THUE"]
    assert (await client.get("/api/phan-anh", headers=h)).status_code == 403  # không thấy nhóm không được giao
    ch = await _tok(client, "chutich")
    comp = (await client.get("/api/compliance", headers=ch)).json()
    assert comp["theo_dau_moi"] and all({"ma", "ten", "dung_han", "cham", "thieu"} <= set(x) for x in comp["theo_dau_moi"])
    for c in comp["chi_tiet"]:
        assert c["dau_moi"], c  # mỗi kỳ chậm/thiếu đều chỉ ra đầu mối chịu trách nhiệm
    src = (await client.get("/api/sources", headers=ch)).json()
    assert next(x for x in src if x["ma"] == "KHO_DL_DAN_CU")["dau_moi"][0]["ma"] == "CATP"
    rem = (await client.get("/api/reminders", headers=await _tok(client, "canbo1"))).json()
    assert all("dau_moi" in r and "cua_dau_moi_toi" in r for r in rem)


async def test_edit_requires_unit_admin_and_is_isolated(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    await seed_tenant("nenh", with_sample=True)
    qt = await _tok(client, "qtphuong")
    body = {"ma": "DIENLUC", "ten": "Công ty Điện lực", "cap": "chuyen_nganh", "noi_dung": "Phối hợp di dời đường điện",
            "trach_nhiem": [{"nhom": "cong_trinh", "vai_tro": "phoi_hop", "noi_dung": "Di dời hạ tầng điện"}], "phieu_nguon": ["D"],
            "chi_tieu": ["NQ01-08b"], "nguoi_lien_he": "Nguyễn Văn Điện", "dien_thoai": "0222 3822 999"}
    assert (await client.post("/api/dau-moi", json=body, headers=qt)).status_code == 201
    assert (await client.post("/api/dau-moi", json=body, headers=qt)).status_code == 409
    assert (await client.post("/api/dau-moi", json={**body, "ma": "X1", "chi_tieu": ["KHONG-CO"]}, headers=qt)).status_code == 422
    assert (await client.post("/api/dau-moi", json={**body, "ma": "X2", "trach_nhiem": [{"nhom": "ngan_sach", "vai_tro": "sai"}]}, headers=qt)).status_code == 422
    # Không gắn được tài khoản của phường khác
    nenh_users = (await client.get("/api/admin/users", headers=await _tok(client, "nenh.qtphuong"))).json()
    assert (await client.put("/api/dau-moi/DIENLUC", json={**body, "user_ids": [nenh_users[0]["id"]]}, headers=qt)).status_code == 422
    assert (await client.post("/api/dau-moi", json={**body, "ma": "X3"}, headers=await _tok(client, "chutich"))).status_code == 403
    nenh = (await client.get("/api/dau-moi", headers=await _tok(client, "nenh.chutich"))).json()
    assert "DIENLUC" not in {d["ma"] for d in nenh["dau_moi"]}
    assert next(d for d in nenh["dau_moi"] if d["ma"] == "UBND")["ten"] == "UBND phường Nếnh"
    assert (await client.delete("/api/dau-moi/DIENLUC", headers=qt)).status_code == 200


async def test_new_ward_gets_defaults_and_tv_hides_contacts(client):
    from app.dau_moi.service import ensure
    from app.core.db import admin_sessionmaker

    t = await make_tenant("Xã Mẫu", cap="xa")
    async with admin_sessionmaker()() as s:
        rows = await ensure(s, t, "Xã Mẫu")
        await s.commit()
    assert rows[0].ten == "UBND xã Mẫu"
    tv = await make_user(t, "man_hinh_tv")
    j = (await client.get("/api/dau-moi", headers=bearer(await login(client, tv["username"])))).json()
    assert all(d["dien_thoai"] is None and d["tai_khoan"] == [] for d in j["dau_moi"])
