"""Kiểm thử cho các phát hiện I5–I12 và lỗi nhỏ của lượt review cuối."""
import io
from datetime import UTC, datetime
from decimal import Decimal as D
from types import SimpleNamespace

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select

from app.budget.models import BudgetLine
from app.catalog.models import IndicatorPlan
from app.core.db import admin_sessionmaker
from app.core.formatting import parse_vn_number
from app.indicators.status import evaluate
from app.projects.models import CapitalPlan, Disbursement, Project
from seeds.run import purge_sample, seed_platform, seed_tenant
from tests.factories import bearer, login, make_tenant, make_user, uid
from tests.indicators.helpers import make_indicator


def _body(**kw):  # noqa: ANN003
    return {"ky_bao_cao": "2026-10", "gia_tri": "5", "nguon": "Báo cáo", "don_vi_cung_cap": "VP", "thoi_diem_chot": "2026-11-01T00:00:00Z", **kw}


async def _staff(client, t):  # noqa: ANN001
    u = await make_user(t, "nhap_lieu", nhom=["ktxh"])
    return bearer(await login(client, u["username"]))


# I5: loại nguồn chỉ nhận giá trị hợp lệ, không bao giờ nhận "api" từ người dùng
async def test_i5_source_type_enum_and_no_api_from_users(client):
    t = await make_tenant()
    ma = uid("S")
    await make_indicator(t, ma_chi_tieu=ma)
    h = await _staff(client, t)
    assert (await client.post(f"/api/indicators/{ma}/values", json=_body(nguon_loai="api"), headers=h)).status_code == 422
    assert (await client.post(f"/api/indicators/{ma}/values", json=_body(nguon_loai="bat_ky"), headers=h)).status_code == 422
    assert (await client.post(f"/api/indicators/{ma}/values", json=_body(nguon_loai="chuyen_nganh"), headers=h)).status_code == 201


# I6: ô tổng quan không báo "Đạt" khi chưa có dữ liệu
async def test_i6_overview_tiles_no_data_not_green(client):
    t = await make_tenant()
    u = await make_user(t, "lanh_dao")
    tiles = {c["ma"]: c for c in (await client.get("/api/overview", params={"ky": "2026-10"}, headers=bearer(await login(client, u["username"])))).json()["the_chi_so"]}
    assert tiles["DTC-GN"]["status"] == "chua_du_du_lieu" and tiles["DTC-GN"]["thuc_hien"] is None
    assert tiles["PAKN-QH"]["status"] == "chua_du_du_lieu" and tiles["PAKN-QH"]["thuc_hien"] is None


# I7: tỷ lệ giải ngân lớp 1 chỉ tính trên dự án có đủ cả kế hoạch vốn và số giải ngân
async def test_i7_disbursement_rate_uses_complete_projects_only(client):
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        for ma, kh, lk in (("A", 100, 40), ("B", 100, None), ("C", None, 50)):
            p = Project(tenant_id=t, ma_du_an=ma, ten=ma, lop=1, chu_dau_tu="UBND", nguon_von="NS")
            s.add(p)
            await s.flush()
            if kh is not None:
                s.add(CapitalPlan(project_id=p.id, tenant_id=t, nam=2026, ky="2026", ke_hoach_von=D(kh)))
            if lk is not None:
                s.add(Disbursement(project_id=p.id, tenant_id=t, ky="2026-10", luy_ke=D(lk)))
        await s.commit()
    u = await make_user(t, "lanh_dao")
    j = (await client.get("/api/projects/summary", params={"ky": "2026-10"}, headers=bearer(await login(client, u["username"])))).json()
    assert j["ty_le_giai_ngan_ns_phuong"] == 40.0
    assert j["theo_lop"]["1"]["du_so_lieu"] == 1 and j["theo_lop"]["1"]["so_du_an"] == 3


# I8: NaN, vô cực không được nhận làm số liệu
def test_i8_reject_nan_and_infinity():
    for bad in ("nan", "NaN", "inf", "-Infinity", float("nan"), float("inf")):
        with pytest.raises(ValueError):
            parse_vn_number(bad)


async def test_i8_api_rejects_nan(client):
    t = await make_tenant()
    ma = uid("N")
    await make_indicator(t, ma_chi_tieu=ma)
    r = await client.post(f"/api/indicators/{ma}/values", json=_body(gia_tri="nan"), headers=await _staff(client, t))
    assert r.status_code == 422


# I9: nhập lại Excel ngân sách không được ghi đè kỳ đã chốt đối soát
async def test_i9_budget_reimport_cannot_overwrite_reconciled(client):
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        s.add(BudgetLine(tenant_id=t, nam=2026, ky="2026-10", loai="thu", nhom_ma="THUE_CTN", scope="dia_ban", du_toan=D(100), thuc_hien=D(80),
                         nguon_loai="bao_cao_chot", trang_thai_doi_soat="da_doi_soat", ngay_chot=datetime(2026, 11, 3, tzinfo=UTC)))
        await s.commit()
    u = await make_user(t, "nhap_lieu", nhom=["ngan_sach"])
    h = bearer(await login(client, u["username"]))
    wb = Workbook()
    ws = wb.active
    ws.title = "Dữ liệu"
    ws.append(["Kỳ", "Loại", "Mã nhóm", "Mã nhiệm vụ", "Phạm vi", "Dự toán", "Kế hoạch kỳ", "Thực hiện lũy kế", "Ước thực hiện", "Nguồn", "Ngày chốt"])
    ws.append(["2026-10", "thu", "THUE_CTN", "", "dia_ban", 100, "", 999, "", "bao_cao_chot", "05/11/2026"])
    b = io.BytesIO()
    wb.save(b)
    j = (await client.post("/api/import/ngan_sach/preview", files={"file": ("ns.xlsx", b.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, headers=h)).json()
    assert j["loi"] and j["loi"][0]["thong_bao"] == "Kỳ 2026-10 đã chốt đối soát, không được ghi đè"


# I10: xóa dữ liệu minh họa xóa cả kế hoạch minh họa
async def test_i10_purge_removes_sample_plans():
    await seed_platform()
    t = await seed_tenant("viet_yen", with_sample=True)
    await purge_sample("viet_yen")
    async with admin_sessionmaker()() as s:
        n = (await s.execute(select(func.count()).select_from(IndicatorPlan).where(IndicatorPlan.tenant_id == t))).scalar()
    assert n == 0
    await seed_tenant("viet_yen", with_sample=True)


# I11: chỉ tiêu "giảm là tốt" đã chạm mục tiêu cuối thì Đạt kể cả trước năm hạn
def test_i11_lower_is_better_at_final_target_before_deadline():
    hn = SimpleNamespace(chieu="giam_tot", nguong_toan_tu=None, muc_tieu=D(0), muc_tieu_khoang=None, muc_tieu_2030=None, han_muc_tieu_nam=2027)
    assert evaluate(hn, D(0), None, nam=2026).status == "dat"
    assert evaluate(hn, D(3), None, nam=2026).status == "chua_du_du_lieu"


# I12: kỳ báo cáo phải đúng chu kỳ cập nhật của chỉ tiêu
async def test_i12_period_must_match_indicator_cycle(client):
    t = await make_tenant()
    ma = uid("Q")
    await make_indicator(t, ma_chi_tieu=ma, ky_cap_nhat="quy")
    h = await _staff(client, t)
    r = await client.post(f"/api/indicators/{ma}/values", json=_body(ky_bao_cao="2026-10"), headers=h)
    assert r.status_code == 422 and "theo quý" in r.json()["detail"]
    assert (await client.post(f"/api/indicators/{ma}/values", json=_body(ky_bao_cao="2026-Q3"), headers=h)).status_code == 201


# Lỗi nhỏ: kỳ không hợp lệ trả 422 chứ không 500
async def test_minor_invalid_period_is_422(client):
    t = await make_tenant()
    ma = uid("K")
    await make_indicator(t, ma_chi_tieu=ma)
    u = await make_user(t, "lanh_dao")
    r = await client.get(f"/api/indicators/{ma}", params={"ky": "2026-13"}, headers=bearer(await login(client, u["username"])))
    assert r.status_code == 422


# Lỗi nhỏ: chỉ một tiến trình chạy quy tắc hằng đêm
async def test_minor_nightly_run_single_instance():
    from app.alerts.scheduler import nightly_lock

    async with nightly_lock() as got1:
        async with nightly_lock() as got2:
            assert got1 is True and got2 is False
