from datetime import date
from decimal import Decimal as D

from app.core.db import admin_sessionmaker
from app.platform.models import ResidentialGroup
from app.quality_of_life.models import PointOfInterest
from app.services_pakn.models import FeedbackTicket
from tests.factories import bearer, login, make_tenant, make_user
from tests.indicators.helpers import make_indicator


async def _h(client, t, role="lanh_dao"):  # noqa: ANN001
    u = await make_user(t, role)
    return bearer(await login(client, u["username"]))


async def test_edu_env_fields(client):
    t = await make_tenant()
    for ma in ("NQ01-11", "NQ01-12", "NQ01-14", "NQ01-15", "NQ01-16", "DT-HS", "DT-LOP", "DT-TRUONG"):
        await make_indicator(t, ma_chi_tieu=ma, nhom="gd_yt_mt", phan_he="gd_yt_mt", chieu="theo_doi" if ma.startswith("DT") else "tang_tot")
    j = (await client.get("/api/qol/summary", params={"ky": "2026-10"}, headers=await _h(client, t))).json()
    assert {c["ma"] for c in j["giao_duc"]} == {"NQ01-11", "DT-HS", "DT-LOP", "DT-TRUONG"}
    assert {c["ma"] for c in j["y_te"]} == {"NQ01-12"}
    assert {c["ma"] for c in j["moi_truong"]} == {"NQ01-14", "NQ01-15", "NQ01-16"}


async def test_poi_layer_requires_quality_ok(client):
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        s.add_all([
            PointOfInterest(tenant_id=t, loai="truong", ten="Trường đạt", lat=D("21.27"), lng=D("106.1"), chat_luong_du_lieu="dat", cho_phep_hien_thi=True),
            PointOfInterest(tenant_id=t, loai="truong", ten="Chưa đạt chất lượng", lat=D("21.27"), lng=D("106.1"), chat_luong_du_lieu="chua_dat", cho_phep_hien_thi=True),
            PointOfInterest(tenant_id=t, loai="truong", ten="Không cho phép", lat=D("21.27"), lng=D("106.1"), chat_luong_du_lieu="dat", cho_phep_hien_thi=False),
            PointOfInterest(tenant_id=t, loai="diem_moi_truong", ten="Điểm tập kết rác", lat=D("21.27"), lng=D("106.1"), chat_luong_du_lieu="dat", cho_phep_hien_thi=True),
        ])
        await s.commit()
    h = await _h(client, t)
    fc = (await client.get("/api/qol/layers/truong", headers=h)).json()
    assert [f["properties"]["ten"] for f in fc["features"]] == ["Trường đạt"]
    assert (await client.get("/api/qol/layers/khac", headers=h)).status_code == 422


async def test_env_feedback_by_area(client):
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        g = ResidentialGroup(tenant_id=t, ma_tdp="TDP01", ten="Tổ dân phố số 1")
        s.add(g)
        await s.flush()
        for i, (lv, tdp) in enumerate([("moi_truong", g.id), ("moi_truong", g.id), ("moi_truong", None), ("an_ninh", g.id)]):
            s.add(FeedbackTicket(tenant_id=t, ma=f"F{i}", loai_viec=lv, linh_vuc=lv, tdp_id=tdp, ngay_nhan=date(2026, 11, 2),
                                 han_xu_ly=date(2026, 11, 9), so_ngay_quy_dinh=5, trang_thai="dang_xu_ly"))
        await s.commit()
    j = (await client.get("/api/qol/env-feedback", params={"tu": "2026-10-01", "den": "2026-11-30"}, headers=await _h(client, t))).json()
    assert {x["khu_vuc"]: x["so_phan_anh"] for x in j} == {"Tổ dân phố số 1": 2, "Chưa xác định địa bàn": 1}
