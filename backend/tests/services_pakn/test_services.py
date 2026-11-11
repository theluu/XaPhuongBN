from datetime import date

from sqlalchemy import select

from app.core.db import admin_sessionmaker, tenant_session
from app.platform.models import SharedCatalog
from app.services_pakn.models import AdminServiceStat, FeedbackTicket
from app.services_pakn.service import add_working_days, due_soon, pakn_sink
from tests.factories import bearer, login, make_tenant, make_user

TODAY = date(2026, 11, 11)


async def _cat():
    async with admin_sessionmaker()() as s:
        for ma, han in (("moi_truong", 5), ("dat_dai", 15)):
            if not (await s.execute(select(SharedCatalog).where(SharedCatalog.loai == "loai_pakn", SharedCatalog.ma == ma))).scalar():
                s.add(SharedCatalog(loai="loai_pakn", ma=ma, ten=ma, thuoc_tinh={"han_xu_ly_ngay": han}))
        await s.commit()


async def _h(client, t, role="lanh_dao", nhom=None):  # noqa: ANN001
    u = await make_user(t, role, nhom=nhom)
    return bearer(await login(client, u["username"]))


async def stat(t, ngay, bo_phan="Một cửa", **kw):  # noqa: ANN001, ANN003
    base = dict(tiep_nhan=10, giai_quyet=8, dung_han=7, qua_han=1, truc_tuyen=6, nguon="bieu_mau", trang_thai="da_xac_nhan", linh_vuc="HOTICH")
    base.update(kw)
    async with admin_sessionmaker()() as s:
        s.add(AdminServiceStat(tenant_id=t, ngay=ngay, bo_phan=bo_phan, **base))
        await s.commit()


def test_working_days_skip_weekend():
    assert add_working_days(date(2026, 11, 6), 1) == date(2026, 11, 9)  # thứ Sáu + 1 ngày làm việc = thứ Hai
    assert add_working_days(date(2026, 11, 9), 5) == date(2026, 11, 16)


async def test_tthc_group_by(client):
    t = await make_tenant()
    await stat(t, date(2026, 11, 2))
    await stat(t, date(2026, 11, 3), bo_phan="Địa chính")
    await stat(t, date(2026, 11, 10))
    h = await _h(client, t)
    r = (await client.get("/api/tthc/summary", params={"tu": "2026-11-01", "den": "2026-11-30", "group": "tuan"}, headers=h)).json()
    assert [x["ky"] for x in r["theo_ky"]] == ["2026-W45", "2026-W46"]
    assert r["theo_ky"][0]["tiep_nhan"] == 20 and r["theo_ky"][0]["dung_han_pct"] == 87.5
    assert {b["bo_phan"]: b["tiep_nhan"] for b in r["theo_bo_phan"]} == {"Một cửa": 20, "Địa chính": 10}
    r = (await client.get("/api/tthc/summary", params={"tu": "2026-11-01", "den": "2026-11-30", "group": "thang", "bo_phan": "Địa chính"}, headers=h)).json()
    assert r["theo_ky"] == [{"ky": "2026-11", "tiep_nhan": 10, "giai_quyet": 8, "dung_han": 7, "qua_han": 1, "truc_tuyen": 6,
                             "dung_han_pct": 87.5, "truc_tuyen_pct": 60.0, "co_so_tam_thoi": False}]


async def test_tam_thoi_vs_confirmed_flag(client):
    t = await make_tenant()
    await stat(t, date(2026, 11, 2), trang_thai="tam_thoi")
    h = await _h(client, t)
    r = (await client.get("/api/tthc/summary", params={"tu": "2026-11-01", "den": "2026-11-30", "group": "thang"}, headers=h)).json()
    assert r["theo_ky"][0]["co_so_tam_thoi"] is True and r["co_so_tam_thoi"] is True


async def test_tthc_form_validation_and_source(client):
    t = await make_tenant()
    hs = await _h(client, t, "nhap_lieu", ["tthc_pakn"])
    bad = {"ngay": "2026-11-05", "bo_phan": "Một cửa", "linh_vuc": "HOTICH", "tiep_nhan": 5, "giai_quyet": 6, "dung_han": 6, "qua_han": 0, "truc_tuyen": 2}
    r = await client.post("/api/tthc/bieu-mau", json=bad, headers=hs)
    assert r.status_code == 422 and r.json()["detail"] == "Số đã giải quyết không được lớn hơn số tiếp nhận"
    r = await client.post("/api/tthc/bieu-mau", json={**bad, "giai_quyet": 5, "dung_han": 4, "qua_han": 2}, headers=hs)
    assert r.json()["detail"] == "Số đúng hạn cộng quá hạn không được lớn hơn số đã giải quyết"
    r = await client.post("/api/tthc/bieu-mau", json={**bad, "giai_quyet": 5, "dung_han": 4, "qua_han": 1}, headers=hs)
    assert r.status_code == 201 and r.json()["nguon"] == "bieu_mau" and r.json()["trang_thai"] == "tam_thoi"


async def test_deadline_rule_per_loai_viec():
    await _cat()
    t = await make_tenant()
    async with tenant_session([t]) as s:
        n = await pakn_sink(s, t, [
            {"ma": "PA-1", "loai_viec": "moi_truong", "linh_vuc": "moi_truong", "ngay_nhan": "2026-11-09", "trang_thai": "dang_xu_ly"},
            {"ma": "PA-2", "loai_viec": "dat_dai", "linh_vuc": "dat_dai", "ngay_nhan": "2026-11-09", "trang_thai": "dang_xu_ly"},
        ])
        await s.commit()
        rows = {r.ma: r for r in (await s.execute(select(FeedbackTicket).where(FeedbackTicket.tenant_id == t))).scalars()}
    assert n == 2
    assert rows["PA-1"].han_xu_ly == date(2026, 11, 16) and rows["PA-2"].han_xu_ly == date(2026, 11, 30)
    async with tenant_session([t]) as s:
        r = await due_soon(s, t, date(2026, 11, 13))
    # PA-1: còn 1/5 ngày làm việc (≤20%) → gần hạn; PA-2: còn 11/15 → chưa
    assert [x["ma"] for x in r] == ["PA-1"] and r[0]["muc"] == "gan_han"
    async with tenant_session([t]) as s:
        r = await due_soon(s, t, date(2026, 11, 17))
    assert [x["ma"] for x in r] == ["PA-1"] and r[0]["muc"] == "qua_han"


async def test_pakn_sink_idempotent_and_no_pii():
    await _cat()
    t = await make_tenant()
    rec = {"ma": "PA-9", "loai_viec": "moi_truong", "linh_vuc": "moi_truong", "ngay_nhan": "2026-11-02", "trang_thai": "tiep_nhan"}
    async with tenant_session([t]) as s:
        await pakn_sink(s, t, [rec])
        await pakn_sink(s, t, [{**rec, "trang_thai": "hoan_thanh", "trang_thai_tra_loi": "da_tra_loi", "danh_gia_hai_long": 4}])
        await s.commit()
        rows = list((await s.execute(select(FeedbackTicket).where(FeedbackTicket.tenant_id == t))).scalars())
    assert len(rows) == 1 and rows[0].trang_thai == "hoan_thanh" and rows[0].danh_gia_hai_long == 4


def test_feedback_has_no_pii_columns():
    cols = set(FeedbackTicket.__table__.c.keys())
    assert not cols & {"ho_ten", "cccd", "so_dinh_danh", "sdt", "so_dien_thoai", "dia_chi", "email"}


async def test_pakn_summary_reply_and_satisfaction(client):
    await _cat()
    t = await make_tenant()
    async with tenant_session([t]) as s:
        await pakn_sink(s, t, [
            {"ma": "A", "loai_viec": "moi_truong", "ngay_nhan": "2026-11-02", "trang_thai": "hoan_thanh", "trang_thai_tra_loi": "da_tra_loi", "danh_gia_hai_long": 5},
            {"ma": "B", "loai_viec": "moi_truong", "ngay_nhan": "2026-11-03", "trang_thai": "hoan_thanh", "trang_thai_tra_loi": "da_tra_loi", "danh_gia_hai_long": 3},
            {"ma": "C", "loai_viec": "dat_dai", "ngay_nhan": "2026-11-04", "trang_thai": "dang_xu_ly"},
            {"ma": "D", "loai_viec": "moi_truong", "ngay_nhan": "2026-10-01", "trang_thai": "dang_xu_ly"},
        ])
        await s.commit()
    h = await _h(client, t)
    r = (await client.get("/api/pakn/summary", params={"tu": "2026-10-01", "den": "2026-11-30"}, headers=h)).json()
    assert r["theo_trang_thai"] == {"tiep_nhan": 0, "dang_xu_ly": 2, "qua_han": 1, "hoan_thanh": 2}
    assert r["ty_le_da_tra_loi_pct"] == 50.0 and r["hai_long_tb"] == 4.0
    lst = (await client.get("/api/pakn/can-don-doc", headers=h)).json()
    assert "D" in [x["ma"] for x in lst]


async def test_nguoi_xem_cannot_read_pakn(client):
    t = await make_tenant()
    h = await _h(client, t, "nguoi_xem")
    assert (await client.get("/api/pakn/summary", headers=h)).status_code == 403
