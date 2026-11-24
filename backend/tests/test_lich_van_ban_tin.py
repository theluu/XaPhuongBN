"""Lịch công tác tuần, văn bản chỉ đạo gắn nhiệm vụ, nguồn tin RSS/Atom (an toàn SSRF) trên dải bản tin."""
from datetime import date, timedelta

import httpx
import pytest

from app.tin_ngoai import service as feed
from seeds.run import seed_platform, seed_tenant
from tests.factories import bearer

RSS = b"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Cong TTDT</title>
<item><title>Phuong to chuc hoi nghi tiep xuc cu tri</title><link>https://cong.example.vn/tin/1</link><guid>tin-1</guid><pubDate>Wed, 11 Nov 2026 14:52:00 +0700</pubDate></item>
<item><title>Ban giao nha dai doan ket</title><link>https://cong.example.vn/tin/2</link><pubDate>Wed, 11 Nov 2026 09:00:00 +0700</pubDate></item>
<item><title>Lien ket xau</title><link>javascript:alert(1)</link></item>
</channel></rss>"""
ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>X</title>
<entry><title>Tin Atom</title><link rel="alternate" href="https://a.example.vn/1"/><id>urn:1</id><updated>2026-11-10T08:00:00Z</updated></entry></feed>"""


async def _tok(client, u):  # noqa: ANN001
    r = await client.post("/api/auth/login", json={"username": u, "password": "Demo@2026"})
    return bearer(r.json()["access_token"])


async def test_week_schedule_today_and_tv(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    h = await _tok(client, "chutich")
    j = (await client.get("/api/lich-cong-tac", headers=h)).json()
    assert [d["thu"] for d in j["ngay"]][0] == "Thứ Hai" and len(j["ngay"]) == 7
    assert sum(len(d["muc"]) for d in j["ngay"]) == 9 and j["co_quyen_sua"] is True
    mon = date.fromisoformat(j["tu"])
    assert mon.weekday() == 0 and mon <= date.today() <= mon + timedelta(days=6)
    nxt = (await client.get("/api/lich-cong-tac", params={"tuan": (mon + timedelta(days=7)).isoformat()}, headers=h)).json()
    assert sum(len(d["muc"]) for d in nxt["ngay"]) == 0
    tv = (await client.get("/api/lich-cong-tac/hom-nay", headers=await _tok(client, "xem"))).json()
    assert all(x["thanh_phan"] == "" for x in tv) and all(x["trang_thai"] != "hoan" for x in tv)
    # Thêm lịch qua Quản lý dữ liệu, giờ sai bị chặn
    row = {"ngay": date.today().isoformat(), "gio_bat_dau": "25:00", "noi_dung": "Họp đột xuất", "loai": "hop", "trang_thai": "chinh_thuc"}
    assert (await client.post("/api/du-lieu/lich_cong_tac", json={"data": row}, headers=h)).status_code == 422
    assert (await client.post("/api/du-lieu/lich_cong_tac", json={"data": {**row, "gio_bat_dau": "16:30"}}, headers=h)).status_code == 201
    assert "Họp đột xuất" in [x["noi_dung"] for x in (await client.get("/api/lich-cong-tac/hom-nay", headers=h)).json()]
    assert (await client.post("/api/du-lieu/lich_cong_tac", json={"data": row}, headers=await _tok(client, "canbo1"))).status_code == 403


async def test_documents_linked_to_tasks(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    h = await _tok(client, "chutich")
    j = (await client.get("/api/van-ban", headers=h)).json()
    assert len(j["van_ban"]) == 5 and j["van_ban"][0]["ngay_ban_hanh"] >= j["van_ban"][-1]["ngay_ban_hanh"]
    tb = next(v for v in j["van_ban"] if v["loai"] == "thong_bao")
    assert tb["tien_do"]["tong"] >= 1 and tb["nhiem_vu"][0]["co_quan_xu_ly"]
    case_id = tb["nhiem_vu"][0]["id"]
    assert tb["id"] in [v["id"] for v in (await client.get("/api/van-ban", params={"nhiem_vu": case_id}, headers=h)).json()["van_ban"]]
    assert len((await client.get("/api/van-ban", params={"q": "trật tự đô thị"}, headers=h)).json()["van_ban"]) == 1
    bad = {"so_ky_hieu": "1/QĐ", "ngay_ban_hanh": date.today().isoformat(), "loai": "quyet_dinh", "co_quan_ban_hanh": "UBND", "trich_yeu": "x",
           "trang_thai": "con_hieu_luc", "lien_ket": "javascript:alert(1)"}
    assert (await client.post("/api/du-lieu/van_ban", json={"data": bad}, headers=h)).status_code == 422
    assert (await client.post("/api/du-lieu/van_ban", json={"data": {**bad, "lien_ket": None, "file_key": "khong-co"}}, headers=h)).status_code == 422
    assert (await client.post("/api/du-lieu/van_ban", json={"data": {**bad, "lien_ket": None, "nhiem_vu_ids": [999999]}}, headers=h)).status_code == 422
    r = await client.post("/api/du-lieu/van_ban", json={"data": {**bad, "lien_ket": "https://vietyen.bacninh.gov.vn/vb/1", "nhiem_vu_ids": [case_id]}}, headers=h)
    assert r.status_code == 201, r.text


def test_parse_rss_atom_and_reject_html():
    items = feed.parse(RSS)
    assert [x["tieu_de"] for x in items] == ["Phuong to chuc hoi nghi tiep xuc cu tri", "Ban giao nha dai doan ket"]  # bỏ liên kết javascript:
    assert items[0]["guid"] == "tin-1" and items[1]["guid"] == "https://cong.example.vn/tin/2" and items[0]["ngay_dang"].year == 2026
    assert feed.parse(ATOM)[0]["lien_ket"] == "https://a.example.vn/1"
    with pytest.raises(feed.FeedError):
        feed.parse(b"<!DOCTYPE html><html><title>Request Rejected</title></html>")
    with pytest.raises(feed.FeedError):
        feed.parse(b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><rss>&a;</rss>')


async def test_fetch_blocks_internal_and_non_https():
    for bad in ("http://cong.example.vn/rss", "https://127.0.0.1/rss", "https://localhost/rss", "ftp://x/y"):
        with pytest.raises(feed.FeedError):
            await feed.fetch(bad)


async def test_refresh_stores_items_and_ticker_shows_them(client, monkeypatch):
    await seed_platform()
    tid = await seed_tenant("viet_yen", with_sample=True)

    async def public(_host):  # noqa: ANN001, ANN202
        return None
    monkeypatch.setattr(feed, "_public_host", public)
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(str(req.url))
        if req.url.path == "/cu":
            return httpx.Response(301, headers={"location": "https://cong.example.vn/rss"})
        if req.url.path == "/chan":
            return httpx.Response(200, content=b"<html><title>Request Rejected</title></html>")
        return httpx.Response(200, content=RSS)
    qt = await _tok(client, "qtphuong")
    assert (await client.patch("/api/admin/tenant", json={"nguon_tin": [{"ten": "Cổng TTĐT", "url": "http://x/rss"}]}, headers=qt)).status_code == 422
    r = await client.patch("/api/admin/tenant", json={"nguon_tin": [{"ten": "Cổng TTĐT phường", "url": "https://cong.example.vn/cu"},
                                                                  {"ten": "Bị chặn", "url": "https://cong.example.vn/chan"}]}, headers=qt)
    assert r.status_code == 200
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        st = await feed.refresh_tenant(tid, c)
        await feed.refresh_tenant(tid, c)  # lấy lại không nhân bản tin
    assert st["https://cong.example.vn/cu"]["ok"] and st["https://cong.example.vn/cu"]["so_tin"] == 2
    assert not st["https://cong.example.vn/chan"]["ok"] and "RSS" in st["https://cong.example.vn/chan"]["loi"]
    assert "https://cong.example.vn/rss" in calls  # theo chuyển hướng
    j = (await client.get("/api/admin/nguon-tin", headers=qt)).json()
    assert len(j["nguon_tin"]) == 2 and j["trang_thai"]["https://cong.example.vn/chan"]["ok"] is False
    bt = (await client.get("/api/bang-tin", headers=await _tok(client, "chutich"))).json()["muc"]
    ngoai = [x for x in bt if x["loai"] == "tin_ngoai"]
    # tin ngày 11/11/2026: chỉ hiện nếu trong 7 ngày gần đây
    if date.today() - date(2026, 11, 11) < timedelta(days=7):
        assert len(ngoai) == 2 and ngoai[0]["nguon"] == "Cổng TTĐT phường"
