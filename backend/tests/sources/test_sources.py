from sqlalchemy import select

from app.core.db import admin_sessionmaker
from app.platform.models import Tenant
from app.sources import registry
from app.sources.models import DataSource, SyncRun
from app.sources.service import ensure_default_sources, module_status, run_sync
from tests.factories import bearer, login, make_tenant, make_user


async def test_source_status_9_of_12(client):
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        await ensure_default_sources(s)
        await s.commit()
    u = await make_user(t, "lanh_dao")
    tok = await login(client, u["username"])
    r = await client.get("/api/sources", headers=bearer(tok))
    assert r.status_code == 200
    kho = next(x for x in r.json() if x["ma"] == "KHO_DL_DAN_CU")
    assert kho["tong_api"] == 12
    assert kho["so_api_ket_noi"] == 12
    assert kho["so_api_tra_du_lieu"] == 9
    assert kho["trang_thai"] == "hoat_dong_mot_phan"


async def test_connector_stores_aggregates_only():
    t = await make_tenant()
    received: list[dict] = []

    async def fake_fetch(source, tenant, ky):  # noqa: ANN001
        return [
            {"chi_so": "dan_so", "ky": ky, "gia_tri": 1000},
            {"chi_so": "dan_so", "ky": ky, "gia_tri": 1, "ho_ten": "Nguyễn Văn A", "so_dinh_danh": "0010"},
        ]

    registry.CONNECTORS["test_pii"] = fake_fetch
    registry.SINKS["test_sink"] = lambda s, tenant_id, records: received.extend(records) or len(records)
    async with admin_sessionmaker()() as s:
        src = DataSource(tenant_id=None, ma=f"T_PII_{t}", ten="Thử", loai="api", co_quan_cung_cap="X", nhom_du_lieu="dan_cu",
                         config={"connector": "test_pii", "sink": "test_sink"}, endpoints=[])
        s.add(src)
        await s.commit()
        run = await run_sync(s, src.id, [t], "2026-10")
    assert received == [{"chi_so": "dan_so", "ky": "2026-10", "gia_tri": 1000}]
    assert run.so_ban_ghi == 1
    assert "1 bản ghi bị loại vì chứa thông tin định danh cá nhân" in run.loi


async def test_sync_failure_marks_source_loi():
    t = await make_tenant()

    async def boom(source, tenant, ky):  # noqa: ANN001
        raise RuntimeError("Hết thời gian chờ kết nối")

    registry.CONNECTORS["test_boom"] = boom
    async with admin_sessionmaker()() as s:
        src = DataSource(tenant_id=None, ma=f"T_BOOM_{t}", ten="Lỗi", loai="api", co_quan_cung_cap="X", nhom_du_lieu="dan_cu",
                         config={"connector": "test_boom", "sink": "noop"}, endpoints=[])
        s.add(src)
        await s.commit()
        run = await run_sync(s, src.id, [t], "2026-10")
        await s.refresh(src)
    assert src.trang_thai == "loi"
    assert "Hết thời gian chờ kết nối" in run.loi


async def test_pakn_connector_sync():
    t = await make_tenant()
    got: list[dict] = []
    registry.SINKS["pakn_test"] = lambda s, tenant_id, records: got.extend(records) or len(records)
    async with admin_sessionmaker()() as s:
        await ensure_default_sources(s)
        src = (await s.execute(select(DataSource).where(DataSource.ma == "PAKN_API"))).scalar_one()
        src.config = {**src.config, "sink": "pakn_test"}
        await s.commit()
        run = await run_sync(s, src.id, [t], "2026-10")
    assert run.so_ban_ghi > 0 and got
    assert all("ho_ten" not in r and "so_dien_thoai" not in r for r in got)
    assert {"ma", "loai_viec", "ngay_nhan", "trang_thai"} <= set(got[0])


async def test_module_status_dang_ket_noi():
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        tenant = await s.get(Tenant, t)
        tenant.modules = {"ktxh": "bat", "cong_trinh": "bat", "gd_yt_mt": "tat"}
        s.add(DataSource(tenant_id=t, ma=f"EXCEL_KTXH_{t}", ten="Excel KT-XH", loai="excel", co_quan_cung_cap="UBND",
                         nhom_du_lieu="ktxh", trang_thai="hoat_dong", config={}, endpoints=[]))
        s.add(DataSource(tenant_id=t, ma=f"API_CT_{t}", ten="API công trình", loai="api", co_quan_cung_cap="Sở XD",
                         nhom_du_lieu="cong_trinh", trang_thai="dang_ket_noi", config={}, endpoints=[]))
        await s.commit()
        st = await module_status(s, t)
    assert st["ktxh"] == "bat"
    assert st["cong_trinh"] == "dang_ket_noi"
    assert st["gd_yt_mt"] == "tat"
    assert st["ngan_sach"] == "dang_ket_noi"  # chưa có nguồn nào


async def test_module_on_when_confirmed_manual_data_exists():
    from tests.indicators.helpers import add_value, make_indicator

    t = await make_tenant()
    iid = await make_indicator(t, nhom="gd_yt_mt", phan_he="gd_yt_mt")
    async with admin_sessionmaker()() as s:
        assert (await module_status(s, t))["gd_yt_mt"] == "dang_ket_noi"
    await add_value(t, iid, "2026-10", 5)
    async with admin_sessionmaker()() as s:
        assert (await module_status(s, t))["gd_yt_mt"] == "bat"
