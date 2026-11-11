from datetime import date
from decimal import Decimal as D

import pytest

from app.core.db import admin_sessionmaker, tenant_session
from app.projects.models import CapitalPlan, Disbursement, Milestone, Project, ProjectIssue
from app.projects.service import overdue_milestones, slow_disbursement
from tests.factories import bearer, login, make_tenant, make_user, uid

TODAY = date(2026, 11, 11)


async def mk(t, lop=1, kh_nam=100, lk=None, lich=None, ma=None, **kw):  # noqa: ANN001
    async with admin_sessionmaker()() as s:
        p = Project(tenant_id=t, ma_du_an=ma or uid("DA"), ten=kw.pop("ten", "Dự án thử"), lop=lop, chu_dau_tu="UBND phường",
                    nguon_von="NS_PHUONG", tong_muc_dt=D(500), dia_diem="TDP 1", **kw)
        s.add(p)
        await s.flush()
        s.add(CapitalPlan(project_id=p.id, tenant_id=t, nam=2026, ky="2026", ke_hoach_von=D(kh_nam)))
        for ky, v in (lich or {}).items():
            s.add(CapitalPlan(project_id=p.id, tenant_id=t, nam=2026, ky=ky, ke_hoach_von=D(v)))
        if lk is not None:
            s.add(Disbursement(project_id=p.id, tenant_id=t, ky="2026-10", luy_ke=D(lk), khoi_luong_pct=D(50), trang_thai_xac_nhan="da_xac_nhan"))
        await s.commit()
        return p.id, p.ma_du_an


async def _tok(client, t, role="lanh_dao"):  # noqa: ANN001
    u = await make_user(t, role)
    return bearer(await login(client, u["username"]))


async def test_disbursement_rate_only_layer1(client):
    t = await make_tenant()
    await mk(t, lop=1, kh_nam=100, lk=40)
    await mk(t, lop=1, kh_nam=100, lk=60)
    await mk(t, lop=2, kh_nam=1000, lk=1000)
    await mk(t, lop=3, kh_nam=50, lk=0)
    j = (await client.get("/api/projects/summary", params={"ky": "2026-10"}, headers=await _tok(client, t))).json()
    assert j["ty_le_giai_ngan_ns_phuong"] == 50.0
    assert j["theo_lop"]["1"]["so_du_an"] == 2 and j["theo_lop"]["2"]["giai_ngan"] == 1000
    assert j["theo_lop"]["3"]["tinh_vao_ty_le"] is False


async def test_duplicate_ma_du_an_rejected():
    t = await make_tenant()
    await mk(t, ma="DA-001")
    with pytest.raises(Exception):
        await mk(t, ma="DA-001")
    t2 = await make_tenant()
    await mk(t2, ma="DA-001")  # đơn vị khác được dùng lại mã


async def test_slow_vs_capital_schedule():
    t = await make_tenant()
    a, _ = await mk(t, lk=30, lich={"2026-10": 50}, ten="Chậm")
    b, _ = await mk(t, lk=60, lich={"2026-10": 50}, ten="Đúng")
    c, _ = await mk(t, lk=10, ten="Không có lịch vốn kỳ")
    async with tenant_session([t]) as s:
        r = await slow_disbursement(s, t, "2026-10")
    assert [x["project_id"] for x in r] == [a]


async def test_milestone_overdue_dau_thau_thi_cong_nghiem_thu():
    t = await make_tenant()
    pid, _ = await mk(t)
    async with admin_sessionmaker()() as s:
        s.add_all([
            Milestone(project_id=pid, tenant_id=t, loai="dau_thau", han=date(2026, 5, 1), ngay_thuc_te=date(2026, 4, 28)),
            Milestone(project_id=pid, tenant_id=t, loai="thi_cong", han=date(2026, 10, 1)),
            Milestone(project_id=pid, tenant_id=t, loai="nghiem_thu", han=date(2026, 11, 1)),
            Milestone(project_id=pid, tenant_id=t, loai="ban_giao", han=date(2026, 12, 31)),
        ])
        await s.commit()
    async with tenant_session([t]) as s:
        r = await overdue_milestones(s, t, TODAY)
    assert sorted(x["loai"] for x in r) == ["nghiem_thu", "thi_cong"]
    assert next(x for x in r if x["loai"] == "thi_cong")["so_ngay_tre"] == 41


async def test_project_issue_fields(client):
    t = await make_tenant()
    pid, ma = await mk(t)
    async with admin_sessionmaker()() as s:
        s.add(ProjectIssue(project_id=pid, tenant_id=t, noi_dung="Vướng GPMB 3 hộ", nguyen_nhan="Chưa thống nhất đơn giá bồi thường",
                           trach_nhiem="Phòng Kinh tế, Hạ tầng", huong_xu_ly="Tổ chức đối thoại lần 2", can_quyet_dinh=True, han=date(2026, 11, 30)))
        await s.commit()
    j = (await client.get(f"/api/projects/{ma}", headers=await _tok(client, t))).json()
    iss = j["vuong_mac"][0]
    assert {"noi_dung", "nguyen_nhan", "trach_nhiem", "huong_xu_ly", "can_quyet_dinh", "han", "trang_thai"} <= set(iss)
    assert iss["can_quyet_dinh"] is True


async def test_project_detail_by_code(client):
    t = await make_tenant()
    _, ma = await mk(t, lk=40, lich={"2026-10": 50})
    h = await _tok(client, t)
    j = (await client.get(f"/api/projects/{ma}", params={"ky": "2026-10"}, headers=h)).json()
    assert j["ma_du_an"] == ma and j["ke_hoach_von_nam"] == 100 and j["giai_ngan_luy_ke"] == 40 and j["ty_le_giai_ngan_pct"] == 40.0
    assert j["lich_von_ky"] == 50 and j["cham_giai_ngan"] is True
    assert (await client.get("/api/projects/KHONG-CO", headers=h)).status_code == 404


async def test_project_list_by_layer_and_no_zero_for_missing(client):
    t = await make_tenant()
    await mk(t, lop=1, lk=None, ten="Chưa có số giải ngân")
    await mk(t, lop=2, lk=5)
    h = await _tok(client, t)
    rows = (await client.get("/api/projects", params={"lop": 1, "ky": "2026-10"}, headers=h)).json()
    assert len(rows) == 1 and rows[0]["giai_ngan_luy_ke"] is None and rows[0]["ty_le_giai_ngan_pct"] is None


async def test_geojson_skips_missing_location(client):
    t = await make_tenant()
    await mk(t, ten="Có tọa độ", lat=D("21.27"), lng=D("106.10"))
    await mk(t, ten="Không tọa độ")
    fc = (await client.get("/api/projects/geojson", headers=await _tok(client, t))).json()
    assert [f["properties"]["ten"] for f in fc["features"]] == ["Có tọa độ"]
    assert fc["features"][0]["geometry"]["coordinates"] == [106.10, 21.27]
