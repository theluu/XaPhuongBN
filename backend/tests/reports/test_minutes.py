from sqlalchemy import select

from app.audit.models import AuditLog
from app.core.db import admin_sessionmaker
from app.reports.models import MeetingSession
from tests.alerts.test_engine import _alert
from tests.factories import bearer, login, make_tenant, make_user


async def test_meeting_minutes_counts(client):
    t = await make_tenant()
    a1 = await _alert(t)
    u = await make_user(t, "lanh_dao")
    h = bearer(await login(client, u["username"]))
    await client.post(f"/api/alerts/{a1.id}/assign", json={"co_quan_xu_ly": "Văn phòng", "nguoi_phu_trach": "Ông A", "han": "2026-11-25"}, headers=h)
    r = await client.post("/api/reports/bien-ban-giao-ban", json={"ky": "2026-10", "thanh_phan": "Bí thư, Chủ tịch, các Phó Chủ tịch", "ket_luan": "Đẩy nhanh thu ngân sách"}, headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf" and r.content[:5] == b"%PDF-"
    async with admin_sessionmaker()() as s:
        m = (await s.execute(select(MeetingSession).where(MeetingSession.tenant_id == t))).scalar_one()
        assert m.so_canh_bao >= 1 and m.so_giao == 1 and m.so_hoan_thanh == 0
        assert (await s.execute(select(AuditLog).where(AuditLog.doi_tuong == f"bien_ban_giao_ban:{m.id}"))).scalar() is not None
    lst = (await client.get("/api/reports/giao-ban", headers=h)).json()
    assert lst[0]["so_giao"] == 1 and lst[0]["ky"] == "2026-10"


async def test_minutes_require_leader(client):
    t = await make_tenant()
    u = await make_user(t, "nguoi_xem")
    r = await client.post("/api/reports/bien-ban-giao-ban", json={"ky": "2026-10"}, headers=bearer(await login(client, u["username"])))
    assert r.status_code == 403


def test_period_names_in_minutes():
    from app.reports.router import _ky_ten

    assert _ky_ten("2026-Q3") == "Quý III/2026" and _ky_ten("2026-10") == "Tháng 10/2026" and _ky_ten("2025") == "Năm 2025"
