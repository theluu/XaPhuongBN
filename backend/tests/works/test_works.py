from datetime import UTC, date, datetime
from decimal import Decimal as D

from app.core.db import admin_sessionmaker, tenant_session
from app.platform.models import Tenant
from app.works.models import Work, WorkProgress
from app.works.service import behind_schedule, missing_decision_dossier, stale_works
from tests.factories import bearer, login, make_tenant, make_user, uid
from tests.indicators.helpers import make_indicator

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"\x00" * 64
TODAY = date(2026, 11, 11)


async def mk_work(t, ma=None, lat=D("21.27"), lng=D("106.10"), **kw):  # noqa: ANN001, ANN003
    async with admin_sessionmaker()() as s:
        w = Work(tenant_id=t, ma_cong_trinh=ma or uid("CT"), ten=kw.pop("ten", "Công trình thử"), loai="GIAO_THONG",
                 dia_diem="TDP 2", lat=lat, lng=lng, don_vi_thuc_hien="Công ty Xây dựng A", ngay_kc=date(2026, 3, 1),
                 ngay_ht=kw.pop("ngay_ht", date(2026, 12, 31)), **kw)
        s.add(w)
        await s.commit()
        return w.id, w.ma_cong_trinh


async def add_prog(t, wid, ngay, kh, tt, **kw):  # noqa: ANN001, ANN003
    async with admin_sessionmaker()() as s:
        s.add(WorkProgress(work_id=wid, tenant_id=t, ngay=ngay, ke_hoach_pct=D(kh), thuc_te_pct=D(tt), trang_thai_xac_nhan="da_xac_nhan", **kw))
        await s.commit()


async def _h(client, t, role="lanh_dao", nhom=None):  # noqa: ANN001
    u = await make_user(t, role, nhom=nhom)
    return bearer(await login(client, u["username"])), u


async def test_work_fields(client):
    t = await make_tenant()
    wid, ma = await mk_work(t, chat_luong="dat", camera_url="https://camera.example/ct1")
    await add_prog(t, wid, date(2026, 11, 5), 60, 55, gpmb="Còn 2 hộ chưa bàn giao", vuong_mac="Thiếu mặt bằng thi công")
    h, _ = await _h(client, t)
    j = (await client.get(f"/api/works/{ma}", headers=h)).json()
    for k in ["don_vi_thuc_hien", "ngay_kc", "ngay_ht", "chat_luong", "camera_url", "dia_diem", "tien_do"]:
        assert k in j
    assert j["tien_do"][-1] | {"anh_keys": []} == j["tien_do"][-1] and j["tien_do"][-1]["gpmb"] == "Còn 2 hộ chưa bàn giao"
    assert j["moi_nhat"]["ke_hoach_pct"] == 60 and j["moi_nhat"]["thuc_te_pct"] == 55 and j["moi_nhat"]["cham"] is True


async def test_geojson_skips_invalid_location(client):
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        (await s.get(Tenant, t)).config = {"ban_do": {"tam": [21.27, 106.1], "zoom": 14, "bbox": [21.24, 106.06, 21.30, 106.14]}}
        await s.commit()
    await mk_work(t, ten="Hợp lệ")
    await mk_work(t, ten="Ngoài ranh giới", lat=D("10.80"), lng=D("106.70"))
    await mk_work(t, ten="Đánh dấu sai", toa_do_hop_le=False)
    await mk_work(t, ten="Không tọa độ", lat=None, lng=None)
    h, _ = await _h(client, t)
    fc = (await client.get("/api/works/geojson", headers=h)).json()
    assert [f["properties"]["ten"] for f in fc["features"]] == ["Hợp lệ"]


async def test_works_require_evidence(client):
    t = await make_tenant()
    _, ma = await mk_work(t)
    hs, _ = await _h(client, t, "nhap_lieu", ["cong_trinh"])
    hb, _ = await _h(client, t, "xac_nhan", ["cong_trinh"])
    body = {"ngay": "2026-11-08", "ke_hoach_pct": 60, "thuc_te_pct": 58}
    pid = (await client.post(f"/api/works/{ma}/progress", json=body, headers=hs)).json()["id"]
    r = await client.post(f"/api/works/progress/{pid}/confirm", headers=hb)
    assert r.status_code == 422 and r.json()["detail"] == "Tiến độ công trình cần có minh chứng (ảnh hiện trường hoặc biên bản)"
    key = (await client.post("/api/files", files={"file": ("a.png", PNG, "image/png")}, headers=hs)).json()["key"]
    pid2 = (await client.post(f"/api/works/{ma}/progress", json={**body, "anh_keys": [key]}, headers=hs)).json()["id"]
    assert (await client.post(f"/api/works/progress/{pid2}/confirm", headers=hb)).status_code == 200


async def test_upload_rejects_pdf_as_photo(client):
    t = await make_tenant()
    _, ma = await mk_work(t)
    hs, _ = await _h(client, t, "nhap_lieu", ["cong_trinh"])
    key = (await client.post("/api/files", files={"file": ("bb.pdf", PDF, "application/pdf")}, headers=hs)).json()["key"]
    r = await client.post(f"/api/works/{ma}/progress", json={"ngay": "2026-11-08", "ke_hoach_pct": 60, "thuc_te_pct": 58, "anh_keys": [key]}, headers=hs)
    assert r.status_code == 422 and r.json()["detail"] == "Ảnh hiện trường phải là tệp ảnh (JPG, PNG, WEBP)"
    r = await client.post(f"/api/works/{ma}/progress", json={"ngay": "2026-11-08", "ke_hoach_pct": 60, "thuc_te_pct": 58, "minh_chung_keys": [key]}, headers=hs)
    assert r.status_code == 201


async def test_alert_issue_needs_decision_missing_dossier():
    t = await make_tenant()
    a, _ = await mk_work(t, ten="Cần quyết định, chưa hồ sơ")
    b, _ = await mk_work(t, ten="Cần quyết định, đủ hồ sơ")
    await add_prog(t, a, date(2026, 11, 5), 50, 40, vuong_mac="GPMB", can_quyet_dinh=True)
    await add_prog(t, b, date(2026, 11, 5), 50, 40, vuong_mac="GPMB", can_quyet_dinh=True, minh_chung_keys=["k1"])
    async with tenant_session([t]) as s:
        r = await missing_decision_dossier(s, t)
    assert [x["work_id"] for x in r] == [a]


async def test_work_weekly_stale():
    t = await make_tenant()
    a, _ = await mk_work(t, ten="Cũ")
    b, _ = await mk_work(t, ten="Mới")
    c, _ = await mk_work(t, ten="Chưa có báo cáo")
    d, _ = await mk_work(t, ten="Đã hoàn thành", trang_thai="hoan_thanh")
    await add_prog(t, a, date(2026, 10, 25), 50, 50)
    await add_prog(t, b, date(2026, 11, 6), 50, 50)
    async with tenant_session([t]) as s:
        r = await stale_works(s, t, TODAY)
    assert sorted(x["work_id"] for x in r) == sorted([a, c])


async def test_behind_schedule_and_late_milestone():
    t = await make_tenant()
    a, _ = await mk_work(t, ten="Chậm")
    b, _ = await mk_work(t, ten="Trễ hạn hoàn thành", ngay_ht=date(2026, 10, 31))
    await add_prog(t, a, date(2026, 11, 5), 60, 45)
    await add_prog(t, b, date(2026, 11, 5), 100, 92)
    async with tenant_session([t]) as s:
        r = {x["work_id"]: x for x in await behind_schedule(s, t, TODAY)}
    assert r[a]["chenh_pct"] == 15 and r[a]["tre_han_ngay"] is None
    assert r[b]["tre_han_ngay"] == 11


async def test_urban_indicators_include_cay_xanh(client):
    t = await make_tenant()
    await make_indicator(t, ma_chi_tieu="DT-CX", ten="Diện tích cây xanh", nhom="cong_trinh", phan_he="cong_trinh")
    await make_indicator(t, ma_chi_tieu="NQ01-08b", ten="Đường được chiếu sáng", nhom="cong_trinh", phan_he="cong_trinh")
    h, _ = await _h(client, t)
    j = (await client.get("/api/works/summary", params={"ky": "2026-10"}, headers=h)).json()
    assert {"DT-CX", "NQ01-08b"} <= {c["ma"] for c in j["chi_tieu_do_thi"]}
    assert set(j) >= {"so_cong_trinh", "so_cham", "so_tre_han", "so_can_quyet_dinh", "chi_tieu_do_thi"}
