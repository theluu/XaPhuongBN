import io
from decimal import Decimal as D

import pytest
from openpyxl import Workbook, load_workbook
from sqlalchemy import func, select

from app.core.db import admin_sessionmaker
from app.core.formatting import parse_vn_number
from app.indicators.models import IndicatorValue
from app.services_pakn.models import AdminServiceStat
from tests.factories import bearer, login, make_tenant, make_user
from tests.indicators.helpers import make_indicator

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_parse_vn_number():
    assert parse_vn_number("1.234,5") == D("1234.5")
    assert parse_vn_number("12,5") == D("12.5")
    assert parse_vn_number("1.234.567") == D("1234567")
    assert parse_vn_number("98.6") == D("98.6")
    assert parse_vn_number(12.5) == D("12.5")
    assert parse_vn_number(7) == D("7")
    for empty in ("", "  ", "-", "—", None):
        assert parse_vn_number(empty) is None
    with pytest.raises(ValueError):
        parse_vn_number("abc")


async def _setup(client):  # noqa: ANN001
    t = await make_tenant()
    await make_indicator(t, ma_chi_tieu="NQ01-12")
    u = await make_user(t, "nhap_lieu", nhom=["ktxh", "tthc_pakn"])
    return t, bearer(await login(client, u["username"]))


async def test_template_download_has_guide_and_codes(client):
    t, h = await _setup(client)
    r = await client.get("/api/import/templates/chi_tieu", headers=h)
    assert r.status_code == 200 and r.headers["content-type"].startswith(XLSX)
    wb = load_workbook(io.BytesIO(r.content))
    assert {"Dữ liệu", "Hướng dẫn", "Danh mục"} <= set(wb.sheetnames)
    assert [c.value for c in wb["Dữ liệu"][1]][:3] == ["Mã chỉ tiêu", "Kỳ báo cáo", "Giá trị"]
    assert "NQ01-12" in [c.value for c in wb["Danh mục"]["A"]]


def _xlsx(header: list[str], rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Dữ liệu"
    ws.append(header)
    for r in rows:
        ws.append(r)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


HDR = ["Mã chỉ tiêu", "Kỳ báo cáo", "Giá trị", "Dự báo/ước", "Nguồn", "Đơn vị cung cấp", "Thời điểm chốt", "Loại nguồn", "Ghi chú/Lý do"]


def _row(ma="NQ01-12", gt="98,6"):  # noqa: ANN001
    return [ma, "2026-10", gt, "", "BHXH thành phố", "Bảo hiểm xã hội", "05/11/2026", "chuyen_nganh", ""]


async def _preview(client, h, data, name="so_lieu.xlsx", ctype=XLSX, loai="chi_tieu"):  # noqa: ANN001
    return await client.post(f"/api/import/{loai}/preview", files={"file": (name, data, ctype)}, headers=h)


async def test_preview_reports_row_numbers(client):
    t, h = await _setup(client)
    rows = [_row() for _ in range(5)] + [_row(ma="NQ01-99")]
    j = (await _preview(client, h, _xlsx(HDR, rows))).json()
    assert j["hop_le"] == 5
    assert {"dong": 7, "cot": "Mã chỉ tiêu", "thong_bao": "Mã chỉ tiêu NQ01-99 không có trong danh mục"} in j["loi"]


async def test_commit_all_or_nothing(client):
    t, h = await _setup(client)
    j = (await _preview(client, h, _xlsx(HDR, [_row(), _row(gt="mười")]))).json()
    assert any(e["cot"] == "Giá trị" for e in j["loi"])
    r = await client.post("/api/import/chi_tieu/commit", json={"preview_id": j["preview_id"]}, headers=h)
    assert r.status_code == 422
    async with admin_sessionmaker()() as s:
        assert (await s.execute(select(func.count()).select_from(IndicatorValue).where(IndicatorValue.tenant_id == t))).scalar() == 0


async def test_commit_creates_tam_thoi_with_source(client):
    t, h = await _setup(client)
    j = (await _preview(client, h, _xlsx(HDR, [_row()]), name="bhyt_t10.xlsx")).json()
    r = await client.post("/api/import/chi_tieu/commit", json={"preview_id": j["preview_id"]}, headers=h)
    assert r.status_code == 200 and r.json()["da_nhap"] == 1
    async with admin_sessionmaker()() as s:
        v = (await s.execute(select(IndicatorValue).where(IndicatorValue.tenant_id == t))).scalar_one()
    assert v.trang_thai == "tam_thoi" and v.gia_tri == D("98.6") and v.nguon_loai == "chuyen_nganh"
    assert v.ly_do == "Nhập từ tệp bhyt_t10.xlsx"
    r = await client.post("/api/import/chi_tieu/commit", json={"preview_id": j["preview_id"]}, headers=h)
    assert r.status_code == 409  # không nhập trùng một lần xem trước


async def test_empty_cell_imports_null(client):
    t, h = await _setup(client)
    j = (await _preview(client, h, _xlsx(HDR, [_row(gt="")]))).json()
    assert not j["loi"]
    await client.post("/api/import/chi_tieu/commit", json={"preview_id": j["preview_id"]}, headers=h)
    async with admin_sessionmaker()() as s:
        assert (await s.execute(select(IndicatorValue.gia_tri).where(IndicatorValue.tenant_id == t))).scalar() is None


async def test_import_csv_and_xlsx(client):
    t, h = await _setup(client)
    csv = ("Ngày;Bộ phận;Lĩnh vực;Tiếp nhận;Giải quyết;Đúng hạn;Quá hạn;Trực tuyến\n"
           "05/11/2026;Một cửa;HOTICH;20;18;17;1;12\n06/11/2026;Một cửa;HOTICH;15;20;10;0;5\n").encode("utf-8-sig")
    j = (await _preview(client, h, csv, name="tthc.csv", ctype="text/csv", loai="tthc")).json()
    assert j["hop_le"] == 1 and j["loi"] == [{"dong": 3, "cot": "Giải quyết", "thong_bao": "Số đã giải quyết không được lớn hơn số tiếp nhận"}]
    csv_ok = csv.decode("utf-8-sig").splitlines()[:2]
    j = (await _preview(client, h, ("\n".join(csv_ok) + "\n").encode(), name="tthc.csv", ctype="text/csv", loai="tthc")).json()
    await client.post("/api/import/tthc/commit", json={"preview_id": j["preview_id"]}, headers=h)
    async with admin_sessionmaker()() as s:
        row = (await s.execute(select(AdminServiceStat).where(AdminServiceStat.tenant_id == t))).scalar_one()
    assert row.tiep_nhan == 20 and row.trang_thai == "tam_thoi" and row.nguon == "bieu_mau"


async def test_rejects_non_spreadsheet(client):
    t, h = await _setup(client)
    r = await _preview(client, h, b"MZ\x90\x00binary", name="x.exe", ctype="application/octet-stream")
    assert r.status_code == 422 and r.json()["detail"] == "Chỉ nhận tệp Excel (.xlsx) hoặc CSV"


async def test_wrong_template_header(client):
    t, h = await _setup(client)
    r = await _preview(client, h, _xlsx(["Cột lạ"], [["x"]]))
    assert r.status_code == 422 and "biểu mẫu" in r.json()["detail"]


async def test_import_respects_group_permission(client):
    t = await make_tenant()
    await make_indicator(t, ma_chi_tieu="NS-1", nhom="ngan_sach", phan_he="ngan_sach")
    u = await make_user(t, "nhap_lieu", nhom=["ktxh"])
    h = bearer(await login(client, u["username"]))
    j = (await _preview(client, h, _xlsx(HDR, [_row(ma="NS-1")]))).json()
    assert j["loi"][0]["thong_bao"] == "Bạn không có quyền nhập số liệu nhóm ngan_sach"


async def test_dynamic_form_from_spec(client):
    t, h = await _setup(client)
    spec = (await client.get("/api/import/templates/tthc/spec", headers=h)).json()
    assert [c["ten"] for c in spec["cot"]][:2] == ["Ngày", "Bộ phận"] and spec["cot"][0]["kieu"] == "ngay"
    r = await client.post("/api/import/tthc/rows", json={"rows": [{"Ngày": "07/11/2026", "Bộ phận": "Một cửa", "Lĩnh vực": "HOTICH", "Tiếp nhận": 3,
                                                                    "Giải quyết": 3, "Đúng hạn": 3, "Quá hạn": 0, "Trực tuyến": 1}]}, headers=h)
    assert r.status_code == 200 and r.json()["da_nhap"] == 1
