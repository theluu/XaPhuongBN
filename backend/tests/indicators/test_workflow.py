from sqlalchemy import select

from app.audit.models import AuditLog
from app.core.db import admin_sessionmaker
from tests.factories import bearer, login, make_tenant, make_user
from tests.indicators.helpers import add_plan, add_value, make_indicator

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def body(v="85", **kw):
    return {"ky_bao_cao": "2026-10", "gia_tri": v, "nguon": "Báo cáo tháng 10", "don_vi_cung_cap": "Văn phòng UBND",
            "thoi_diem_chot": "2026-10-31T00:00:00Z", **kw}


async def _setup(client, nhom="ktxh", **ind_kw):
    t = await make_tenant()
    ma = f"WF-{t}"
    iid = await make_indicator(t, ma_chi_tieu=ma, nhom=nhom, phan_he=nhom, **ind_kw)
    await add_plan(t, iid, "2026-10", 100)
    staff = await make_user(t, "nhap_lieu", nhom=[nhom])
    boss = await make_user(t, "xac_nhan", nhom=[nhom])
    return t, iid, ma, await login(client, staff["username"]), await login(client, boss["username"]), staff, boss


async def test_submit_creates_tam_thoi(client):
    t, iid, ma, st, bt, *_ = await _setup(client)
    r = await client.post(f"/api/indicators/{ma}/values", json=body(), headers=bearer(st))
    assert r.status_code == 201, r.text
    assert r.json()["trang_thai"] == "tam_thoi"
    c = (await client.get(f"/api/indicators/{ma}", params={"ky": "2026-10"}, headers=bearer(bt))).json()
    assert c["data_state"] == "tam_thoi" and c["thuc_hien"] == 85


async def test_viewer_cannot_submit(client):
    t, iid, ma, *_ = await _setup(client)
    v = await make_user(t, "nguoi_xem")
    r = await client.post(f"/api/indicators/{ma}/values", json=body(), headers=bearer(await login(client, v["username"])))
    assert r.status_code == 403


async def test_self_confirm_forbidden(client):
    t = await make_tenant()
    ma = f"SELF-{t}"
    await make_indicator(t, ma_chi_tieu=ma)
    both = await make_user(t, "chuyen_nganh", nhom=["ktxh"])  # có cả nhập và duyệt
    tok = await login(client, both["username"])
    vid = (await client.post(f"/api/indicators/{ma}/values", json=body(), headers=bearer(tok))).json()["id"]
    r = await client.post(f"/api/values/{vid}/confirm", headers=bearer(tok))
    assert r.status_code == 403
    assert r.json()["detail"] == "Người nhập không được tự xác nhận"


async def test_confirm_requires_duyet_on_nhom(client):
    t, iid, ma, st, bt, *_ = await _setup(client)
    vid = (await client.post(f"/api/indicators/{ma}/values", json=body(), headers=bearer(st))).json()["id"]
    other = await make_user(t, "xac_nhan", nhom=["gd_yt_mt"])
    r = await client.post(f"/api/values/{vid}/confirm", headers=bearer(await login(client, other["username"])))
    assert r.status_code == 403
    r = await client.post(f"/api/values/{vid}/confirm", headers=bearer(bt))
    assert r.status_code == 200
    c = (await client.get(f"/api/indicators/{ma}", params={"ky": "2026-10"}, headers=bearer(bt))).json()
    assert c["data_state"] == "da_xac_nhan" and c["nguoi_xac_nhan"]


async def test_edit_confirmed_creates_new_version(client):
    t, iid, ma, st, bt, *_ = await _setup(client)
    v1 = (await client.post(f"/api/indicators/{ma}/values", json=body("85"), headers=bearer(st))).json()["id"]
    await client.post(f"/api/values/{v1}/confirm", headers=bearer(bt))
    r = await client.post(f"/api/indicators/{ma}/values", json=body("92", ly_do="Cập nhật số chốt"), headers=bearer(st))
    assert r.json()["version"] == 2
    c = (await client.get(f"/api/indicators/{ma}", params={"ky": "2026-10"}, headers=bearer(bt))).json()
    assert c["thuc_hien"] == 85 and c["co_so_moi_cho_xac_nhan"] is True
    await client.post(f"/api/values/{r.json()['id']}/confirm", headers=bearer(bt))
    c = (await client.get(f"/api/indicators/{ma}", params={"ky": "2026-10"}, headers=bearer(bt))).json()
    assert c["thuc_hien"] == 92 and c["co_so_moi_cho_xac_nhan"] is False
    assert len(c["lich_su"]) == 2


async def test_edit_confirmed_requires_reason(client):
    t, iid, ma, st, bt, *_ = await _setup(client)
    v1 = (await client.post(f"/api/indicators/{ma}/values", json=body("85"), headers=bearer(st))).json()["id"]
    await client.post(f"/api/values/{v1}/confirm", headers=bearer(bt))
    r = await client.post(f"/api/indicators/{ma}/values", json=body("92"), headers=bearer(st))
    assert r.status_code == 422
    assert r.json()["detail"] == "Sửa số đã xác nhận phải ghi lý do"


async def test_reject_requires_reason(client):
    t, iid, ma, st, bt, *_ = await _setup(client)
    vid = (await client.post(f"/api/indicators/{ma}/values", json=body(), headers=bearer(st))).json()["id"]
    r = await client.post(f"/api/values/{vid}/reject", json={"ly_do": " "}, headers=bearer(bt))
    assert r.status_code == 422
    r = await client.post(f"/api/values/{vid}/reject", json={"ly_do": "Sai kỳ chốt"}, headers=bearer(bt))
    assert r.status_code == 200
    c = (await client.get(f"/api/indicators/{ma}", params={"ky": "2026-10"}, headers=bearer(bt))).json()
    assert c["thuc_hien"] is None and c["data_state"] == "chua_co_qua_han"


async def test_confirm_requires_evidence_when_flagged(client):
    t, iid, ma, st, bt, *_ = await _setup(client, can_minh_chung=True)
    vid = (await client.post(f"/api/indicators/{ma}/values", json=body(), headers=bearer(st))).json()["id"]
    r = await client.post(f"/api/values/{vid}/confirm", headers=bearer(bt))
    assert r.status_code == 422
    assert r.json()["detail"] == "Chỉ tiêu này cần có minh chứng trước khi xác nhận"
    f = await client.post("/api/files", files={"file": ("anh.png", PNG, "image/png")}, headers=bearer(st))
    assert f.status_code == 201, f.text
    vid2 = (await client.post(f"/api/indicators/{ma}/values", json=body(minh_chung_keys=[f.json()["key"]]), headers=bearer(st))).json()["id"]
    assert (await client.post(f"/api/values/{vid2}/confirm", headers=bearer(bt))).status_code == 200


async def test_inbox_lists_pending_for_my_groups(client):
    t, iid, ma, st, bt, *_ = await _setup(client)
    vid = (await client.post(f"/api/indicators/{ma}/values", json=body(), headers=bearer(st))).json()["id"]
    r = await client.get("/api/values/inbox", headers=bearer(bt))
    assert vid in [x["id"] for x in r.json()]
    other = await make_user(t, "xac_nhan", nhom=["gd_yt_mt"])
    r = await client.get("/api/values/inbox", headers=bearer(await login(client, other["username"])))
    assert vid not in [x["id"] for x in r.json()]


async def test_confirm_writes_audit_before_after(client):
    t, iid, ma, st, bt, *_ = await _setup(client)
    vid = (await client.post(f"/api/indicators/{ma}/values", json=body(), headers=bearer(st))).json()["id"]
    await client.post(f"/api/values/{vid}/confirm", headers=bearer(bt))
    async with admin_sessionmaker()() as s:
        row = (await s.execute(select(AuditLog).where(AuditLog.doi_tuong == f"so_lieu:{vid}:xac_nhan"))).scalar()
    assert row.before == {"trang_thai": "tam_thoi"} and row.after["trang_thai"] == "da_xac_nhan"
