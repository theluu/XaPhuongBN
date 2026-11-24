"""Chuông thông báo: đúng người nhận theo sự kiện, gộp theo việc, đánh dấu đã đọc, không lộ sang người khác."""
from datetime import date, timedelta

from seeds.run import seed_platform, seed_tenant
from tests.factories import bearer


async def _tok(client, u):  # noqa: ANN001
    r = await client.post("/api/auth/login", json={"username": u, "password": "Demo@2026"})
    return bearer(r.json()["access_token"])


async def _noti(client, h):  # noqa: ANN001
    return (await client.get("/api/noti", headers=h)).json()


async def test_events_reach_the_right_people(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    ct, kt, xn, cb = await _tok(client, "chutich"), await _tok(client, "ketoan"), await _tok(client, "xacnhan"), await _tok(client, "canbo1")
    base_cb = (await _noti(client, cb))["chua_doc"]
    # 1. Giao xử lý cảnh báo → người phụ trách (theo họ tên) nhận "giao việc"
    a = next(x for x in (await client.get("/api/alerts", headers=ct)).json() if not x["ho_so"])
    r = await client.post(f"/api/alerts/{a['id']}/assign", headers=ct, json={"co_quan_xu_ly": "Phòng Kinh tế", "nguoi_phu_trach": "Vũ Thị Giang",
                                                                             "han": (date.today() + timedelta(days=5)).isoformat(), "chi_dao": "Báo cáo ngay"})
    assert r.status_code == 200
    j = await _noti(client, cb)
    assert j["chua_doc"] == base_cb + 1
    n = j["muc"][0]
    assert n["loai"] == "giao_viec" and a["tieu_de"] in n["tieu_de"] and n["lien_ket"] == f"/canh-bao?id={a['id']}" and not n["da_doc"]
    # 2. Người phụ trách hoàn thành → người giao nhận "kết quả"
    case = next(x for x in (await client.get("/api/alerts", headers=ct)).json() if x["id"] == a["id"])["ho_so"]
    r = await client.patch(f"/api/cases/{case['id']}", headers=cb, json={"ket_qua": "Đã xử lý", "trang_thai": "hoan_thanh"})
    assert r.status_code == 200, r.text
    assert any(x["loai"] == "ket_qua" and a["tieu_de"] in x["tieu_de"] for x in (await _noti(client, ct))["muc"])
    # 3. Nhập số liệu → người xác nhận nhóm đó nhận "chờ xác nhận"; từ chối → người nhập nhận "từ chối"
    r = await client.post("/api/indicators/NQ01-12/values", headers=cb, json={"ky_bao_cao": "2026-11", "gia_tri": 99.3, "nguon": "BHXH", "don_vi_cung_cap": "BHXH",
                                                                          "thoi_diem_chot": "2026-11-30T00:00:00+07:00"})
    assert r.status_code == 201, r.text
    vid = r.json()["id"]
    assert any(x["loai"] == "cho_xac_nhan" and "BHYT" in x["tieu_de"] for x in (await _noti(client, xn))["muc"])
    assert not any(x["loai"] == "cho_xac_nhan" and "BHYT" in x["tieu_de"] and "2026-11" in x["noi_dung"] for x in (await _noti(client, kt))["muc"])
    await client.post(f"/api/values/{vid}/reject", headers=xn, json={"ly_do": "Thiếu minh chứng"})
    assert any(x["loai"] == "tu_choi" and "Thiếu minh chứng" in x["noi_dung"] for x in (await _noti(client, cb))["muc"])
    # 4. Tin nhắn: gộp một thông báo/cuộc, mở cuộc trao đổi thì đã đọc
    ppl = (await client.get("/api/tin-nhan/nguoi-nhan", headers=ct)).json()["nguoi"]
    xn_id = next(p["id"] for p in ppl if p["username"] == "xacnhan")
    h = (await client.post("/api/tin-nhan/hoi-thoai", headers=ct, json={"thanh_vien_ids": [xn_id], "tin_dau": {"noi_dung": "Anh xem giúp số BHYT"}})).json()["id"]
    await client.post(f"/api/tin-nhan/hoi-thoai/{h}/tin", headers=ct, json={"noi_dung": "Gấp nhé"})
    tin = [x for x in (await _noti(client, xn))["muc"] if x["lien_ket"] == f"/tin-nhan?id={h}"]
    assert len(tin) == 1 and tin[0]["noi_dung"] == "Gấp nhé" and not tin[0]["da_doc"]
    await client.get(f"/api/tin-nhan/hoi-thoai/{h}", headers=xn)
    assert all(x["da_doc"] for x in (await _noti(client, xn))["muc"] if x["lien_ket"] == f"/tin-nhan?id={h}")
    # 5. Thông báo điều hành theo đối tượng
    await client.post("/api/du-lieu/thong_bao", headers=ct, json={"data": {"tieu_de": "Họp khẩn 14h", "muc_do": "khan", "tu_ngay": date.today().isoformat(), "doi_tuong": ["nhap_lieu"]}})
    assert any(x["tieu_de"] == "Họp khẩn 14h" and x["muc_do"] == "khan" for x in (await _noti(client, cb))["muc"])
    assert not any(x["tieu_de"] == "Họp khẩn 14h" for x in (await _noti(client, kt))["muc"])


async def test_read_and_privacy(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    cb, kt = await _tok(client, "canbo1"), await _tok(client, "ketoan")
    j = await _noti(client, cb)
    assert j["chua_doc"] >= 2  # thông báo minh họa
    d = (await client.get("/api/noti/dem", headers=cb)).json()
    assert d["chua_doc"] == j["chua_doc"] and d["moi_nhat"]["id"] == next(x for x in j["muc"] if not x["da_doc"])["id"]
    first = j["muc"][0]["id"]
    assert (await client.post(f"/api/noti/{first}/doc", headers=kt)).status_code == 404  # không đọc được của người khác
    await client.post(f"/api/noti/{first}/doc", headers=cb)
    assert (await _noti(client, cb))["chua_doc"] == j["chua_doc"] - 1
    assert (await client.post("/api/noti/doc-het", headers=cb)).json()["da_doc"] >= 1
    assert (await _noti(client, cb))["chua_doc"] == 0
    assert (await client.get("/api/noti", params={"chi_chua_doc": True}, headers=cb)).json()["muc"] == []
