"""Nhắn tin nội bộ: hội thoại gắn cảnh báo, tệp chỉ thành viên tải, công văn xử lý vào sổ văn bản, chưa đọc, cách ly đơn vị."""
import io

from seeds.run import seed_platform, seed_tenant
from tests.factories import bearer

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


async def _tok(client, u):  # noqa: ANN001
    r = await client.post("/api/auth/login", json={"username": u, "password": "Demo@2026"})
    assert r.status_code == 200, r.text
    return bearer(r.json()["access_token"])


async def _uid(client, h, username):  # noqa: ANN001
    ppl = (await client.get("/api/tin-nhan/nguoi-nhan", headers=h)).json()["nguoi"]
    return next(p["id"] for p in ppl if p["username"] == username)


async def test_alert_thread_with_file_and_dispatch(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    ct, kt, cb = await _tok(client, "chutich"), await _tok(client, "ketoan"), await _tok(client, "canbo1")
    d = (await client.get("/api/tin-nhan/nguoi-nhan", headers=ct)).json()
    assert d["phat_hanh_cong_van"] is True and "xem" not in {p["username"] for p in d["nguoi"]}  # không có tài khoản TV
    alert = next(a for a in (await client.get("/api/alerts", headers=ct)).json() if a["ho_so"])
    kt_id = await _uid(client, ct, "ketoan")
    up = await client.post("/api/tin-nhan/tep", files={"file": ("cong-van-thu-ngan-sach.pdf", io.BytesIO(PDF), "application/pdf")}, headers=ct)
    assert up.status_code == 201
    key = up.json()["key"]
    r = await client.post("/api/tin-nhan/hoi-thoai", headers=ct, json={
        "thanh_vien_ids": [kt_id], "lien_ket_loai": "canh_bao", "lien_ket_id": alert["id"],
        "tin_dau": {"noi_dung": "Đề nghị xử lý ngay, gửi kèm công văn.", "tep_keys": [key],
                    "cong_van": {"so_ky_hieu": "215/UBND-KT", "trich_yeu": "Đôn đốc thu tiền sử dụng đất", "han_thuc_hien": "2026-12-01"}}})
    assert r.status_code == 201, r.text
    hid = r.json()["id"]
    # Người nhận thấy tin chưa đọc, đọc xong về 0
    assert (await client.get("/api/tin-nhan/chua-doc", headers=kt)).json()["tong"] >= 1
    th = (await client.get(f"/api/tin-nhan/hoi-thoai/{hid}", headers=kt)).json()
    assert th["lien_ket_url"] == f"/canh-bao?id={alert['id']}" and th["phat_hanh_cong_van"] is False
    m = th["tin"][-1]
    assert m["cong_van"]["so_ky_hieu"] == "215/UBND-KT" and m["tep"][0]["ten"] == "cong-van-thu-ngan-sach.pdf"
    assert (await client.get(f"/api/tin-nhan/tep/{key}", headers=kt)).status_code == 200
    conv = next(c for c in (await client.get("/api/tin-nhan/hoi-thoai", headers=kt)).json() if c["id"] == hid)
    assert conv["chua_doc"] == 0
    # Công văn vào sổ Văn bản chỉ đạo, gắn nhiệm vụ của cảnh báo; tệp công văn ai trong đơn vị cũng mở được
    vb = next(v for v in (await client.get("/api/van-ban", headers=ct)).json()["van_ban"] if v["so_ky_hieu"] == "215/UBND-KT")
    assert vb["nhiem_vu"] and vb["nhiem_vu"][0]["id"] == alert["ho_so"]["id"] and vb["nguoi_ky"] == "Lê Minh Châu"
    assert (await client.get(f"/api/files/{key}", headers=cb)).status_code == 200
    # Người ngoài hội thoại: không đọc được tin, không tải được tệp riêng
    assert (await client.get(f"/api/tin-nhan/hoi-thoai/{hid}", headers=cb)).status_code == 404
    up2 = await client.post("/api/tin-nhan/tep", files={"file": ("rieng.pdf", io.BytesIO(PDF + b" "), "application/pdf")}, headers=kt)
    k2 = up2.json()["key"]
    assert (await client.post(f"/api/tin-nhan/hoi-thoai/{hid}/tin", json={"noi_dung": "Báo cáo kèm theo", "tep_keys": [k2]}, headers=kt)).status_code == 201
    assert (await client.get(f"/api/tin-nhan/tep/{k2}", headers=cb)).status_code == 404
    assert (await client.get(f"/api/files/{k2}", headers=cb)).status_code == 404
    assert (await client.get(f"/api/files/{k2}", headers=ct)).status_code == 200
    # Cán bộ không phát hành công văn; không gửi tệp của người khác
    r = await client.post(f"/api/tin-nhan/hoi-thoai/{hid}/tin", headers=kt, json={"tep_keys": [k2], "cong_van": {"so_ky_hieu": "1", "trich_yeu": "x"}})
    assert r.status_code == 403
    assert (await client.post(f"/api/tin-nhan/hoi-thoai/{hid}/tin", headers=kt, json={"tep_keys": [key]})).status_code == 422
    assert (await client.post(f"/api/tin-nhan/hoi-thoai/{hid}/tin", headers=kt, json={"noi_dung": "  "})).status_code == 422


async def test_direct_reuse_add_members_tv_and_isolation(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    await seed_tenant("nenh", with_sample=True)
    xn = await _tok(client, "xacnhan")
    cb_id = await _uid(client, xn, "canbo1")
    a = (await client.post("/api/tin-nhan/hoi-thoai", json={"thanh_vien_ids": [cb_id], "tin_dau": {"noi_dung": "Chào em"}}, headers=xn)).json()
    b = (await client.post("/api/tin-nhan/hoi-thoai", json={"thanh_vien_ids": [cb_id]}, headers=xn)).json()
    assert b == {"id": a["id"], "da_co": True}
    assert (await client.post(f"/api/tin-nhan/hoi-thoai/{a['id']}/thanh-vien", json={"user_ids": [await _uid(client, xn, "ketoan")]}, headers=xn)).status_code == 409
    g = (await client.post("/api/tin-nhan/hoi-thoai", json={"thanh_vien_ids": [cb_id], "tieu_de": "Nhóm số liệu quý III"}, headers=xn)).json()
    kt_id = await _uid(client, xn, "ketoan")
    assert (await client.post(f"/api/tin-nhan/hoi-thoai/{g['id']}/thanh-vien", json={"user_ids": [kt_id]}, headers=xn)).json() == {"them": 1}
    th = (await client.get(f"/api/tin-nhan/hoi-thoai/{g['id']}", headers=await _tok(client, "ketoan"))).json()
    assert th["tin"][-1]["he_thong"] and "đã thêm" in th["tin"][-1]["noi_dung"]
    # TV không nhắn tin; không gửi cho người phường khác
    assert (await client.get("/api/tin-nhan/hoi-thoai", headers=await _tok(client, "xem"))).status_code == 403
    nenh = await _tok(client, "nenh.chutich")
    nenh_ct = next(p["id"] for p in (await client.get("/api/tin-nhan/nguoi-nhan", headers=nenh)).json()["nguoi"] if p["username"] == "nenh.xacnhan")
    assert (await client.post("/api/tin-nhan/hoi-thoai", json={"thanh_vien_ids": [nenh_ct]}, headers=xn)).status_code == 422
    assert (await client.get(f"/api/tin-nhan/hoi-thoai/{a['id']}", headers=nenh)).status_code == 404
    # Dữ liệu minh họa: chủ tịch có trao đổi gắn cảnh báo và tin chưa đọc
    ct = await _tok(client, "chutich")
    convs = (await client.get("/api/tin-nhan/hoi-thoai", headers=ct)).json()
    assert any(c["lien_ket_loai"] == "canh_bao" and c["is_sample"] for c in convs)
    assert (await client.get("/api/tin-nhan/chua-doc", headers=await _tok(client, "ketoan"))).json()["tong"] >= 1
