from datetime import UTC, date, datetime
from decimal import Decimal as D

from sqlalchemy import select

from app.alerts.engine import run_rules
from app.alerts.models import Alert
from app.budget.models import BudgetLine
from app.core.db import admin_sessionmaker, tenant_session
from app.projects.models import Milestone, Project
from app.services_pakn.models import FeedbackTicket
from tests.factories import bearer, login, make_tenant, make_user
from tests.indicators.helpers import add_plan, add_value, make_indicator

TODAY = date(2026, 11, 11)
QUALITY = "Đây là cảnh báo chất lượng dữ liệu, chưa kết luận chỉ tiêu không đạt."


async def run(t, today=TODAY, ky="2026-10"):  # noqa: ANN001
    async with tenant_session([t]) as s:
        await run_rules(s, t, today, ky)
        await s.commit()
        return list((await s.execute(select(Alert).where(Alert.tenant_id == t).order_by(Alert.id))).scalars())


async def test_alert_cham_kh():
    t = await make_tenant()
    i = await make_indicator(t, ma_chi_tieu="A1")
    await add_plan(t, i, "2026-10", 100)
    await add_value(t, i, "2026-10", 80)
    al = await run(t)
    a = next(a for a in al if a.rule_ma == "CT_CHAM_KH")
    assert a.loai == "tien_do" and "A1" in a.doi_tuong_ref and a.ghi_chu_chat_luong is None


async def test_progress_alert_uses_period_plan():
    t = await make_tenant()
    i = await make_indicator(t, ma_chi_tieu="Q-TIEN-DO", ky_cap_nhat="quy", luy_ke=True)
    await add_plan(t, i, "2026-Q3", 40)  # kế hoạch lũy kế quý 3 = 40% kế hoạch năm
    await add_plan(t, i, "2026", 100)
    await add_value(t, i, "2026-Q3", 45)  # 45 < 75 (9/12 tháng) nhưng ≥ kế hoạch kỳ → không cảnh báo
    assert not [a for a in await run(t) if a.rule_ma == "CT_CHAM_KH"]


async def test_alert_qua_han_cap_nhat_and_data_alert_separate_type():
    t = await make_tenant()
    i = await make_indicator(t, ma_chi_tieu="THIEU", han_cap_nhat_ngay=10)
    await add_plan(t, i, "2026-10", 100)
    al = await run(t, today=date(2026, 11, 5))  # chưa quá hạn (31/10 + 10 ngày)
    assert not [a for a in al if a.rule_ma == "CT_QUA_HAN_CAP_NHAT"]
    al = await run(t, today=TODAY)
    q = [a for a in al if a.rule_ma == "CT_QUA_HAN_CAP_NHAT"]
    assert len(q) == 1 and q[0].loai == "qua_han" and q[0].ghi_chu_chat_luong == QUALITY
    assert not [a for a in al if a.rule_ma == "CT_CHAM_KH"]


async def test_alert_lech_nguon_phuong_vs_chuyen_nganh():
    t = await make_tenant()
    i = await make_indicator(t, ma_chi_tieu="BHYT")
    await add_value(t, i, "2026-10", "99.1", nguon_loai="phuong")
    await add_value(t, i, "2026-10", "98.6", nguon_loai="chuyen_nganh")
    a = next(a for a in await run(t) if a.rule_ma == "CT_LECH_NGUON")
    assert a.loai == "lech_nguon" and a.ghi_chu_chat_luong == QUALITY and "99,1" in a.mo_ta and "98,6" in a.mo_ta


async def test_alert_unit_not_submitted():
    t = await make_tenant()
    for _ in range(2):
        i = await make_indicator(t, nhom="gd_yt_mt", phan_he="gd_yt_mt", don_vi_chu_quan="Trung tâm Y tế")
        await add_plan(t, i, "2026-10", 1)
    al = [a for a in await run(t) if a.rule_ma == "DV_CHUA_GUI_DU_LIEU"]
    assert len(al) == 1 and al[0].loai == "chua_gui" and "Trung tâm Y tế" in al[0].tieu_de and "2 chỉ tiêu" in al[0].mo_ta


async def test_rules_idempotent():
    t = await make_tenant()
    i = await make_indicator(t)
    await add_plan(t, i, "2026-10", 100)
    await add_value(t, i, "2026-10", 50)
    n1 = len(await run(t))
    n2 = len(await run(t))
    assert n1 == n2 and n1 > 0


async def test_resolved_alert_expires():
    t = await make_tenant()
    i = await make_indicator(t, ma_chi_tieu="HOI-PHUC")
    await add_plan(t, i, "2026-10", 100)
    await add_value(t, i, "2026-10", 50)
    await run(t)
    await add_value(t, i, "2026-10", 120, version=2)
    a = next(a for a in await run(t) if a.rule_ma == "CT_CHAM_KH")
    assert a.trang_thai == "het_hieu_luc"


async def test_budget_project_pakn_rules():
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        s.add(BudgetLine(tenant_id=t, nam=2026, ky="2026-10", loai="chi", nhom_ma="CHI_SN_MT", nhiem_vu="NV_MOITRUONG", scope="ns_phuong",
                         du_toan=D(20), thuc_hien=D(25), nguon_loai="bao_cao_chot", trang_thai_doi_soat="da_doi_soat",
                         ngay_chot=datetime(2026, 11, 3, tzinfo=UTC)))
        p = Project(tenant_id=t, ma_du_an="DA-X", ten="Dự án X", lop=1, chu_dau_tu="UBND", nguon_von="NS_PHUONG")
        s.add(p)
        await s.flush()
        s.add(Milestone(project_id=p.id, tenant_id=t, loai="nghiem_thu", han=date(2026, 10, 1)))
        s.add(FeedbackTicket(tenant_id=t, ma="PA-QH", loai_viec="moi_truong", ngay_nhan=date(2026, 10, 1), han_xu_ly=date(2026, 10, 8),
                             so_ngay_quy_dinh=5, trang_thai="dang_xu_ly"))
        await s.commit()
    codes = {a.rule_ma: a for a in await run(t)}
    assert codes["NS_CHI_VUOT_DT"].muc_do == "cao"
    assert "Nghiệm thu" in codes["DA_QUA_HAN_MOC"].tieu_de and "41 ngày" in codes["DA_QUA_HAN_MOC"].mo_ta
    assert codes["PAKN_QUA_HAN"].muc_do == "cao"
    assert codes["NS_CHI_VUOT_DT"].nhom == "ngan_sach" and codes["DA_QUA_HAN_MOC"].nhom == "dau_tu_cong"


async def _h(client, t, role="lanh_dao", nhom=None):  # noqa: ANN001
    u = await make_user(t, role, nhom=nhom)
    return bearer(await login(client, u["username"]))


async def _alert(t):  # noqa: ANN001
    i = await make_indicator(t)
    await add_plan(t, i, "2026-10", 100)
    await add_value(t, i, "2026-10", 50)
    return next(a for a in await run(t) if a.rule_ma == "CT_CHAM_KH")


async def test_assign_creates_case_and_case_fields(client):
    t = await make_tenant()
    a = await _alert(t)
    h = await _h(client, t)
    body = {"co_quan_xu_ly": "Phòng Kinh tế", "nguoi_phu_trach": "Ông Nguyễn Văn B", "han": "2026-11-25", "chi_dao": "Rà soát, báo cáo nguyên nhân"}
    r = await client.post(f"/api/alerts/{a.id}/assign", json=body, headers=h)
    assert r.status_code == 200, r.text
    case = r.json()["ho_so"]
    for k in ["co_quan_xu_ly", "nguoi_phu_trach", "nguyen_nhan", "hanh_dong", "han", "trang_thai", "ket_qua"]:
        assert k in case
    assert r.json()["trang_thai"] == "da_giao"


async def test_assign_only_lanh_dao(client):
    t = await make_tenant()
    a = await _alert(t)
    h = await _h(client, t, "nhap_lieu", ["ktxh"])
    r = await client.post(f"/api/alerts/{a.id}/assign", json={"co_quan_xu_ly": "X", "nguoi_phu_trach": "Y", "han": "2026-11-25"}, headers=h)
    assert r.status_code == 403


async def test_case_close_requires_ket_qua_and_extension_needs_deadline(client):
    t = await make_tenant()
    a = await _alert(t)
    h = await _h(client, t)
    cid = (await client.post(f"/api/alerts/{a.id}/assign", json={"co_quan_xu_ly": "X", "nguoi_phu_trach": "Y", "han": "2026-11-25"}, headers=h)).json()["ho_so"]["id"]
    r = await client.patch(f"/api/cases/{cid}", json={"trang_thai": "hoan_thanh"}, headers=h)
    assert r.status_code == 422 and r.json()["detail"] == "Hoàn thành hồ sơ phải ghi kết quả xử lý"
    r = await client.patch(f"/api/cases/{cid}", json={"trang_thai": "gia_han"}, headers=h)
    assert r.status_code == 422 and r.json()["detail"] == "Gia hạn phải ghi hạn mới"
    r = await client.patch(f"/api/cases/{cid}", json={"trang_thai": "hoan_thanh", "nguyen_nhan": "Chậm nhập số", "hanh_dong": "Đã đôn đốc",
                                                       "ket_qua": "Đã cập nhật số liệu kỳ 10"}, headers=h)
    assert r.status_code == 200 and r.json()["trang_thai"] == "hoan_thanh"
    al = (await client.get("/api/alerts", headers=h)).json()
    assert next(x for x in al if x["id"] == a.id)["trang_thai"] == "hoan_thanh"


async def test_alerts_hidden_without_permission(client):
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        s.add(BudgetLine(tenant_id=t, nam=2026, ky="2026-10", loai="chi", nhom_ma="CHI_SN_MT", scope="ns_phuong", du_toan=D(20), thuc_hien=D(25),
                         nguon_loai="bao_cao_chot", ngay_chot=datetime(2026, 11, 3, tzinfo=UTC)))
        await s.commit()
    await run(t)
    viewer = await _h(client, t, "nguoi_xem")
    assert not [x for x in (await client.get("/api/alerts", headers=viewer)).json() if x["nhom"] == "ngan_sach"]
    boss = await _h(client, t)
    assert [x for x in (await client.get("/api/alerts", headers=boss)).json() if x["nhom"] == "ngan_sach"]


async def test_week_list_for_leaders(client):
    t = await make_tenant()
    await _alert(t)
    r = (await client.get("/api/alerts/tuan-nay", headers=await _h(client, t))).json()
    assert r and {"id", "tieu_de", "muc_do", "loai", "trang_thai", "link"} <= set(r[0])


async def test_budget_alert_uses_catalog_names():
    from app.platform.models import SharedCatalog

    async with admin_sessionmaker()() as s:
        if not (await s.execute(select(SharedCatalog).where(SharedCatalog.loai == "nhom_chi", SharedCatalog.ma == "CHI_SN_MT"))).scalar():
            s.add(SharedCatalog(loai="nhom_chi", ma="CHI_SN_MT", ten="Chi sự nghiệp môi trường"))
            await s.commit()
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        s.add(BudgetLine(tenant_id=t, nam=2026, ky="2026-10", loai="chi", nhom_ma="CHI_SN_MT", scope="ns_phuong", du_toan=D(20), thuc_hien=D(25),
                         nguon_loai="bao_cao_chot", ngay_chot=datetime(2026, 11, 3, tzinfo=UTC)))
        await s.commit()
    a = next(a for a in await run(t) if a.rule_ma == "NS_CHI_VUOT_DT")
    assert a.tieu_de == "Chi sự nghiệp môi trường vượt dự toán"
