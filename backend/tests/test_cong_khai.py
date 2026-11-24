"""Trang công khai theo phường: chọn chỉ tiêu, công bố kỳ, chỉ số đã xác nhận mới ra ngoài, nhận diện phường theo tên miền, đăng nhập theo tên miền."""
from app.core.db import admin_sessionmaker
from app.platform.models import Tenant
from tests.factories import PASSWORD, bearer, login, make_tenant, make_user
from tests.indicators.helpers import add_value, make_indicator

KY = "2026-10"


async def _ward(slug: str, host: str) -> int:
    tid = await make_tenant(f"Phường {slug}")
    async with admin_sessionmaker()() as s:
        t = await s.get(Tenant, tid)
        t.config = {"slug": slug, "ten_mien": [host]}
        await s.commit()
    return tid


async def test_publish_only_confirmed_selected(client):
    tid = await _ward("an-binh", "anbinh.example.vn")
    ok = await make_indicator(tid, ma_chi_tieu="CK-OK", ten="Chỉ tiêu đã xác nhận")
    tam = await make_indicator(tid, ma_chi_tieu="CK-TAM", ten="Chỉ tiêu tạm thời")
    await make_indicator(tid, ma_chi_tieu="CK-AN", ten="Chỉ tiêu không chọn")
    await make_indicator(tid, ma_chi_tieu="CK-HC", ten="Chỉ tiêu hạn chế", phan_loai_thong_tin="han_che")
    await add_value(tid, ok, KY, 42)
    await add_value(tid, tam, KY, 7, trang_thai="tam_thoi")
    ld = bearer(await login(client, (await make_user(tid, "lanh_dao"))["username"]))
    xem = bearer(await login(client, (await make_user(tid, "nguoi_xem"))["username"]))

    # Chưa công bố → trang công khai chưa có bản
    r = await client.get("/api/cong-khai/an-binh")
    assert r.status_code == 200 and r.json()["ban"] is None

    # Không được chọn chỉ tiêu hạn chế; người xem không được sửa cấu hình
    body = {"chi_tieu": ["CK-OK", "CK-TAM"], "tong_hop": [], "xu_huong_ngan_sach": False}
    assert (await client.put("/api/cong-khai/quan-tri", json={**body, "chi_tieu": ["CK-HC"]}, headers=ld)).status_code == 422
    assert (await client.put("/api/cong-khai/quan-tri", json=body, headers=xem)).status_code == 403
    assert (await client.put("/api/cong-khai/quan-tri", json=body, headers=ld)).status_code == 200
    assert (await client.post("/api/cong-khai/quan-tri/cong-bo", json={"ky": KY}, headers=xem)).status_code == 403
    r = await client.post("/api/cong-khai/quan-tri/cong-bo", json={"ky": KY}, headers=ld)
    assert r.status_code == 200, r.text

    # Số liệu nội bộ đổi sau khi công bố không lộ ra ngoài
    await add_value(tid, ok, KY, 99, version=2)
    j = (await client.get("/api/cong-khai/an-binh")).json()
    cards = {c["ma"]: c for c in j["ban"]["du_lieu"]["chi_tieu"]}
    assert set(cards) == {"CK-OK", "CK-TAM"}
    assert cards["CK-OK"]["thuc_hien"] == 42 and cards["CK-OK"]["da_xac_nhan"] is True
    assert cards["CK-TAM"]["thuc_hien"] is None and cards["CK-TAM"]["status"] == "dang_cap_nhat"
    assert "value_id" not in cards["CK-OK"] and "nguoi_xac_nhan" not in cards["CK-OK"]
    assert j["ky_da_cong_bo"] == [KY]
    dump = str(j["ban"]["du_lieu"])
    assert "chuyen_muc" in j["ban"]["du_lieu"]
    for secret in ("vuong_mac", "camera_url", "gpmb", "nguoi_xac_nhan", "value_id"):
        assert secret not in dump

    # Danh sách phường ở tên miền chung
    lst = (await client.get("/api/cong-khai")).json()["don_vi"]
    assert any(w["slug"] == "an-binh" and w["ban_moi_nhat"]["ky"] == KY for w in lst)

    # Thu hồi → trang công khai không còn bản
    bid = r.json()["id"]
    assert (await client.post(f"/api/cong-khai/quan-tri/{bid}/thu-hoi", json={"ly_do": "Số liệu cần rà soát"}, headers=ld)).status_code == 200
    assert (await client.get("/api/cong-khai/an-binh")).json()["ban"] is None


async def test_resolve_host_and_unknown_slug(client):
    await _ward("binh-minh", "binhminh.example.vn")
    r = await client.get("/api/cong-khai/xac-dinh", headers={"host": "BinhMinh.example.vn:443"})
    assert r.json()["don_vi"]["slug"] == "binh-minh"
    assert (await client.get("/api/cong-khai/xac-dinh", headers={"host": "khac.example.vn"})).json()["don_vi"] is None
    assert (await client.get("/api/cong-khai/khong-co")).status_code == 404


async def test_login_restricted_to_ward_domain(client):
    a = await _ward("phuong-a", "a.example.vn")
    b = await _ward("phuong-b", "b.example.vn")
    ua = await make_user(a, "lanh_dao")
    await make_user(b, "lanh_dao")
    body = {"username": ua["username"], "password": PASSWORD}
    assert (await client.post("/api/auth/login", json=body, headers={"host": "b.example.vn"})).status_code == 401
    assert (await client.post("/api/auth/login", json=body, headers={"host": "a.example.vn"})).status_code == 200
    assert (await client.post("/api/auth/login", json=body)).status_code == 200  # tên miền chung

    p = await make_tenant("Nền tảng", cap="nen_tang")
    pa = await make_user(p, "quan_tri_nen_tang")
    assert (await client.post("/api/auth/login", json={"username": pa["username"], "password": PASSWORD},
                              headers={"host": "b.example.vn"})).status_code == 200


async def test_platform_sets_public_address(client):
    from app.cong_khai.service import tenant_for_host

    p = await make_tenant("Nền tảng", cap="nen_tang")
    h = bearer(await login(client, (await make_user(p, "quan_tri_nen_tang"))["username"]))
    x = await make_tenant("Phường X")
    y = await make_tenant("Phường Y")
    r = await client.patch(f"/api/platform/tenants/{x}", json={"slug": "phuong-x", "ten_mien": ["https://PX.example.vn/"]}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["ten_mien"] == ["px.example.vn"] and r.json()["slug"] == "phuong-x"
    assert (await client.patch(f"/api/platform/tenants/{y}", json={"slug": "phuong-x"}, headers=h)).status_code == 409
    assert (await client.patch(f"/api/platform/tenants/{y}", json={"ten_mien": ["px.example.vn"]}, headers=h)).status_code == 409
    assert (await client.patch(f"/api/platform/tenants/{y}", json={"slug": "Có Dấu"}, headers=h)).status_code == 422
    assert (await client.patch(f"/api/platform/tenants/{y}", json={"ten_mien": ["khong hop le"]}, headers=h)).status_code == 422
    async with admin_sessionmaker()() as s:
        assert (await tenant_for_host(s, "px.example.vn")).id == x


async def test_quarter_period_service_index_and_directives(client):
    tid = await _ward("quy-ba", "quyba.example.vn")
    ok = await make_indicator(tid, ma_chi_tieu="CK-Q", ten="Chỉ tiêu quý", ky_cap_nhat="quy")
    await add_value(tid, ok, "2026-Q3", 5)
    ld = bearer(await login(client, (await make_user(tid, "lanh_dao"))["username"]))
    assert (await client.put("/api/cong-khai/quan-tri", json={"chi_tieu": ["CK-Q"], "tong_hop": []}, headers=ld)).status_code == 200
    # điểm vượt tối đa bị từ chối; hợp lệ thì lưu
    bad = {"ky": "2026-09", "tieu_chi": [{"ten": "Công khai, minh bạch", "diem": 20, "toi_da": 18}]}
    assert (await client.put("/api/cong-khai/quan-tri/chi-so-phuc-vu", json=bad, headers=ld)).status_code == 422
    good = {"ky": "2026-09", "tieu_chi": [{"ten": "Công khai, minh bạch", "diem": 17, "toi_da": 18}, {"ten": "Tiến độ giải quyết", "diem": 19, "toi_da": 20}],
            "xep_hang": 5, "tong_don_vi": 99}
    assert (await client.put("/api/cong-khai/quan-tri/chi-so-phuc-vu", json=good, headers=ld)).status_code == 200
    r = await client.post("/api/cong-khai/quan-tri/cong-bo", json={"ky": "2026-Q3"}, headers=ld)
    assert r.status_code == 200, r.text
    j = (await client.get("/api/cong-khai/quy-ba", params={"ky": "2026-Q3"})).json()
    d = j["ban"]["du_lieu"]
    assert j["ban"]["ky"] == "2026-Q3" and d["chi_tieu"][0]["thuc_hien"] == 5
    assert d["chuyen_muc"]["phuc_vu"]["tong_diem"] == 36 and d["chuyen_muc"]["phuc_vu"]["xep_hang"] == 5
    assert (await client.get("/api/cong-khai/quy-ba", params={"ky": "2026-13"})).status_code == 422
    lst = (await client.get("/api/cong-khai")).json()
    assert any(x["slug"] == "quy-ba" and x["phuc_vu_diem"] == 36 for x in lst["so_sanh"])


async def test_highlight_falls_back_to_latest_confirmed_month(client):
    """Số liệu nổi bật: tháng công bố còn chờ đối soát → hiện số đã chốt tháng trước (ghi rõ tháng), không để "Đang cập nhật"."""
    from decimal import Decimal

    from app.budget.models import BudgetLine
    from app.core.db import tenant_session

    tid = await _ward("hoa-binh", "hoabinh.example.vn")
    async with tenant_session([tid]) as s:
        for ky, ds, th in (("2026-09", "da_doi_soat", 80), ("2026-10", "cho_doi_soat", 95)):
            s.add(BudgetLine(tenant_id=tid, nam=2026, ky=ky, loai="thu", nhom_ma="THUE_CTN", scope="dia_ban", du_toan=Decimal(120 * 10**9),
                             ke_hoach_ky=Decimal(75 * 10**9), thuc_hien=Decimal(th * 10**9), nguon_loai="bao_cao_chot", trang_thai_doi_soat=ds))
        await s.commit()
    ld = bearer(await login(client, (await make_user(tid, "lanh_dao"))["username"]))
    body = {"chi_tieu": [], "tong_hop": ["NS-THU-DB"], "xu_huong_ngan_sach": False}
    assert (await client.put("/api/cong-khai/quan-tri", json=body, headers=ld)).status_code == 200
    assert (await client.post("/api/cong-khai/quan-tri/cong-bo", json={"ky": KY}, headers=ld)).status_code == 200
    th = {c["ma"]: c for c in (await client.get("/api/cong-khai/hoa-binh")).json()["ban"]["du_lieu"]["tong_hop"]}["NS-THU-DB"]
    assert th["da_xac_nhan"] is True and th["thuc_hien"] == 80 and th["ky_so_lieu"] == "2026-09"
