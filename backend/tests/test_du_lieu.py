"""Quản lý dữ liệu tập trung: mọi bộ dữ liệu xem/thêm/sửa/xóa theo quyền nhóm; sửa số đã xác nhận phải xác nhận lại; xóa có lý do, có nhật ký."""
from sqlalchemy import select

from app.audit.models import AuditLog
from app.core.db import admin_sessionmaker
from app.data_admin.registry import DATASETS
from seeds.run import seed_platform, seed_tenant
from tests.factories import bearer, login, make_tenant, make_user


async def _tok(client, username):  # noqa: ANN001
    r = await client.post("/api/auth/login", json={"username": username, "password": "Demo@2026"})
    assert r.status_code == 200, r.text
    return bearer(r.json()["access_token"])


async def _full(client, tid):  # noqa: ANN001
    """Phiên quản trị nền tảng vào quản trị đơn vị: đủ quyền mọi nhóm."""
    p = await make_tenant("Nền tảng", cap="nen_tang")
    u = await make_user(p, "quan_tri_nen_tang")
    h = bearer(await login(client, u["username"]))
    r = await client.post(f"/api/platform/tenants/{tid}/vao-quan-tri", headers=h)
    return bearer(r.json()["access_token"])


async def test_every_dataset_lists_and_exports(client):
    await seed_platform()
    tid = await seed_tenant("viet_yen", with_sample=True)
    h = await _full(client, tid)
    cat = (await client.get("/api/du-lieu", headers=h)).json()["bo_du_lieu"]
    assert {d["key"] for d in cat} == {d.key for d in DATASETS}
    for d in DATASETS:
        r = await client.get(f"/api/du-lieu/{d.key}", params={"size": 5, "q": "a"}, headers=h)
        assert r.status_code == 200, (d.key, r.text)
        j = (await client.get(f"/api/du-lieu/{d.key}", params={"size": 5}, headers=h)).json()
        assert j["schema"]["sua"] and j["schema"]["xoa"]
        csv = await client.get(f"/api/du-lieu/{d.key}/csv", headers=h)
        assert csv.status_code == 200 and csv.text.startswith("﻿ID,")
    by = {d["key"]: d for d in cat}
    assert by["ngan_sach"]["so_ban_ghi"] > 0 and by["ngan_sach"]["so_minh_hoa"] == by["ngan_sach"]["so_ban_ghi"]


async def test_role_scope_of_catalog(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    async def cat(u):  # noqa: ANN001
        return {d["key"]: d for d in (await client.get("/api/du-lieu", headers=await _tok(client, u))).json()["bo_du_lieu"]}
    thue = await cat("thue")
    assert set(thue) == {"ngan_sach", "so_lieu"} and thue["ngan_sach"]["sua"] and thue["ngan_sach"]["xoa"]
    # Bảng chỉ tiêu, kế hoạch giao, nhiệm vụ trọng tâm: UBND (lãnh đạo, quản trị) lập — DT II.1
    ct = await cat("chutich")
    assert all(ct[k]["them"] and ct[k]["sua"] and ct[k]["xoa"] for k in ("chi_tieu", "ke_hoach", "nhiem_vu", "thong_bao", "lich_cong_tac", "van_ban"))
    assert not ct["so_lieu"]["them"] and not ct["du_an"]["them"] and "lãnh đạo xem" in ct["du_an"]["quyen_mo_ta"].lower()
    assert ct["phan_anh"]["them_link"] is None and (await cat("canbo1"))["phan_anh"]["them_link"] == "/phan-anh?tiep_nhan=1"
    cb = await cat("canbo1")
    assert "ngan_sach" in cb and cb["ngan_sach"]["sua"] and not cb["ngan_sach"]["xoa"]  # nhập được, không xóa
    assert "chi_tieu" not in cb and "ke_hoach" not in cb  # cán bộ nhập liệu không sửa chỉ tiêu, kế hoạch giao
    qt = await cat("qtphuong")
    assert qt["chi_tieu"]["sua"] and qt["dia_ban"]["xoa"] and "ngan_sach" not in qt  # quản trị không thấy nhóm nhạy cảm
    assert (await client.get("/api/du-lieu", headers=await _tok(client, "xem"))).json()["bo_du_lieu"] == []


async def test_budget_crud_and_reconciled_row_requires_reason(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    h = await _tok(client, "ketoan")
    row = {"nam": 2026, "ky": "2026-11", "loai": "thu", "nhom_ma": "LE_PHI", "scope": "ns_phuong", "du_toan": "8000000000",
           "thuc_hien": "500000000", "nguon_loai": "bao_cao_chot"}
    r = await client.post("/api/du-lieu/ngan_sach", json={"data": row}, headers=h)
    assert r.status_code == 201, r.text
    nid = r.json()["id"]
    assert r.json()["trang_thai_doi_soat"] == "cho_doi_soat" and r.json()["is_sample"] is False
    assert (await client.post("/api/du-lieu/ngan_sach", json={"data": {**row, "ky": "2025-11"}}, headers=h)).status_code == 422  # kỳ khác năm
    assert (await client.post("/api/du-lieu/ngan_sach", json={"data": {**row, "nhiem_vu": "KHONG_CO"}}, headers=h)).status_code == 422
    r = await client.put(f"/api/du-lieu/ngan_sach/{nid}", json={"data": {"thuc_hien": "650000000"}}, headers=h)
    assert r.json()["thuc_hien"] == "650000000"
    # Dòng đã đối soát: sửa phải có lý do và quay về chờ đối soát
    j = (await client.get("/api/du-lieu/ngan_sach", params={"loc_trang_thai_doi_soat": "da_doi_soat", "size": 1}, headers=h)).json()
    old = j["rows"][0]
    assert (await client.put(f"/api/du-lieu/ngan_sach/{old['id']}", json={"data": {"thuc_hien": "1"}}, headers=h)).status_code == 422
    r = await client.put(f"/api/du-lieu/ngan_sach/{old['id']}", json={"data": {"thuc_hien": "1"}, "ly_do": "Sai số báo cáo chốt"}, headers=h)
    assert r.json()["trang_thai_doi_soat"] == "cho_doi_soat" and r.json()["can_xac_nhan_lai"] is True
    # Xóa: cán bộ nhập liệu không xóa được; xóa bắt buộc lý do; có nhật ký nguyên trạng
    assert (await client.post("/api/du-lieu/ngan_sach/xoa", json={"ids": [nid], "ly_do": "x"}, headers=await _tok(client, "canbo1"))).status_code == 403
    assert (await client.post("/api/du-lieu/ngan_sach/xoa", json={"ids": [nid], "ly_do": " "}, headers=h)).status_code == 422
    r = await client.post("/api/du-lieu/ngan_sach/xoa", json={"ids": [nid], "ly_do": "Nhập trùng"}, headers=h)
    assert r.json() == {"da_xoa": 1}
    async with admin_sessionmaker()() as s:
        log = (await s.execute(select(AuditLog).where(AuditLog.doi_tuong == "du_lieu:ngan_sach:xoa").order_by(AuditLog.id.desc()))).scalars().first()
    assert log.before["ban_ghi"][0]["id"] == nid and log.after["ly_do"] == "Nhập trùng"


async def test_indicator_value_edit_resets_confirmation_and_row_group_permission(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    h = await _tok(client, "sogddt")  # cơ quan chuyên ngành nhóm giáo dục – y tế – môi trường
    j = (await client.get("/api/du-lieu/so_lieu", params={"size": 200}, headers=h)).json()
    assert j["rows"] and all(r["indicator_id__nhan"].split(" – ")[0] in {"NQ01-11", "NQ01-12", "NQ01-14", "NQ01-15", "NQ01-16", "DT-TRUONG", "DT-LOP", "DT-HS"}
                             for r in j["rows"])  # chỉ thấy chỉ tiêu nhóm được giao
    conf = next(r for r in j["rows"] if r["trang_thai"] == "da_xac_nhan")
    assert (await client.put(f"/api/du-lieu/so_lieu/{conf['id']}", json={"data": {"gia_tri": "1.5"}}, headers=h)).status_code == 422  # thiếu lý do
    r = await client.put(f"/api/du-lieu/so_lieu/{conf['id']}", json={"data": {"gia_tri": "1.5"}, "ly_do": "Điều chỉnh theo báo cáo Sở"}, headers=h)
    assert r.status_code == 200 and r.json()["trang_thai"] == "tam_thoi" and r.json()["nguoi_xac_nhan_ten"] is None and r.json()["gia_tri"] == "1.5"
    other = (await client.get("/api/du-lieu/so_lieu", params={"size": 200}, headers=await _tok(client, "xacnhan"))).json()["rows"]
    kt = next(x for x in other if x["indicator_id__nhan"].startswith("NQ01-13"))
    r = await client.put(f"/api/du-lieu/so_lieu/{kt['id']}", json={"data": {"gia_tri": "1"}, "ly_do": "x"}, headers=h)
    assert r.status_code == 403  # bản ghi thuộc nhóm KT-XH không được sửa
    # Không chuyển số liệu sang chỉ tiêu nhóm khác
    r = await client.put(f"/api/du-lieu/so_lieu/{conf['id']}", json={"data": {"indicator_id": kt["indicator_id"]}, "ly_do": "x"}, headers=h)
    assert r.status_code == 403


async def test_isolation_and_validation(client):
    await seed_platform()
    await seed_tenant("viet_yen", with_sample=True)
    nenh = await seed_tenant("nenh", with_sample=True)
    hn = await _full(client, nenh)
    vy_row = (await client.get("/api/du-lieu/diem", headers=await _full(client, (await _vy_id())))).json()["rows"][0]
    assert (await client.put(f"/api/du-lieu/diem/{vy_row['id']}", json={"data": {"ten": "X"}}, headers=hn)).status_code == 404
    bad = {"loai": "truong", "ten": "Trường A", "lat": "48.85", "lng": "106.08", "chat_luong_du_lieu": "dat", "cho_phep_hien_thi": True}
    assert (await client.post("/api/du-lieu/diem", json={"data": bad}, headers=hn)).status_code == 422
    r = await client.post("/api/du-lieu/diem", json={"data": {**bad, "lat": "21.24"}}, headers=hn)
    assert r.status_code == 201
    dup = {"ma_du_an": "DA-01", "ten": "Trùng", "lop": "1", "chu_dau_tu": "UBND", "nguon_von": "NS_PHUONG", "trang_thai": "dang_thuc_hien"}
    assert (await client.post("/api/du-lieu/du_an", json={"data": dup}, headers=hn)).status_code == 409
    assert (await client.post("/api/du-lieu/phan_anh", json={"data": {"tieu_de": "x"}}, headers=hn)).status_code == 409  # thêm tại màn nghiệp vụ
    assert (await client.post("/api/du-lieu/so_lieu", json={"data": {"indicator_id": 1, "ky_bao_cao": "2026-13"}}, headers=hn)).status_code == 422
    ct = (await client.get("/api/du-lieu/chi_tieu", params={"size": 1}, headers=hn)).json()["rows"][0]
    assert (await client.post("/api/du-lieu/chi_tieu/xoa", json={"ids": [ct["id"]], "ly_do": "thử"}, headers=hn)).status_code == 409  # còn số liệu


async def _vy_id() -> int:
    from app.platform.models import Tenant

    async with admin_sessionmaker()() as s:
        return (await s.execute(select(Tenant.id).where(Tenant.ma_dvhc == "P-VIETYEN"))).scalar_one()


async def test_every_dataset_add_edit_delete_round_trip(client):
    """Mọi bộ dữ liệu cho thêm mới đều thêm → sửa → xóa được với dữ liệu hợp lệ sinh từ khai báo trường."""
    from datetime import date

    await seed_platform()
    tid = await seed_tenant("viet_yen", with_sample=True)
    h = await _full(client, tid)
    today = date.today()
    sample = {"text": "Mục thử nghiệm", "textarea": "Nội dung thử", "int": 3, "dec": "12.5", "date": today.isoformat(),
              "datetime": f"{today.isoformat()}T08:00:00+07:00", "time": "09:30", "bool": True, "ky": f"{today.year}-{today.month:02d}"}
    done = []
    for d in DATASETS:
        if not d.them:
            continue
        j = (await client.get(f"/api/du-lieu/{d.key}", params={"size": 1}, headers=h)).json()
        data = {}
        for f in j["schema"]["truong"]:
            if f["readonly"]:
                continue
            k = f["kind"]
            if k == "enum":
                v = next(iter(o for o in f["options"] if o != ""))
            elif k == "multi":
                v = []
            elif k == "cat":
                v = j["lua_chon"]["cat"][f["cat"]][0]["value"]
            elif k == "ref":
                v = j["lua_chon"]["ref"][f["ref"]][0]["value"]
            elif k == "refmulti":
                v = [j["lua_chon"]["ref"][f["ref"]][0]["value"]] if j["lua_chon"]["ref"].get(f["ref"]) else []
            elif k == "file":
                v = None
            elif f["name"] in ("lat",):
                v = "21.27"
            elif f["name"] in ("lng",):
                v = "106.09"
            elif f["name"] == "lien_ket":
                v = "https://example.gov.vn/x"
            elif f["name"] == "danh_gia_hai_long":
                v = 4
            elif f["name"] in ("nam",):
                v = today.year
            elif f["name"] in ("tiep_nhan", "giai_quyet", "dung_han", "qua_han", "truc_tuyen"):
                v = {"tiep_nhan": 5, "giai_quyet": 4, "dung_han": 3, "qua_han": 1, "truc_tuyen": 2}[f["name"]]
            elif f["name"] == "nhom_tuoi":
                v = "0-4"
            elif k == "text" and (f["create_only"] or f["name"] in ("ma_tdp", "ma_cu", "ma", "don_vi_ma")):
                v = f"TEST-{d.key[:6].upper()}"
            else:
                v = sample.get(k, "x")
            data[f["name"]] = v
        r = await client.post(f"/api/du-lieu/{d.key}", json={"data": data}, headers=h)
        assert r.status_code == 201, (d.key, r.text)
        rid = r.json()["id"]
        first = next(f for f in j["schema"]["truong"] if not f["readonly"] and not f["create_only"] and f["kind"] in ("text", "textarea", "dec", "int", "date"))
        nv = {"text": "Đã sửa", "textarea": "Đã sửa", "dec": "13", "int": 4, "date": today.isoformat()}[first["kind"]]
        if first["name"] in ("ma_tdp", "ma_cu"):
            nv = f"TEST2-{d.key[:4].upper()}"
        if first["name"] in ("tiep_nhan",):
            nv = 6
        r = await client.put(f"/api/du-lieu/{d.key}/{rid}", json={"data": {first["name"]: nv}, "ly_do": "thử"}, headers=h)
        assert r.status_code == 200, (d.key, r.text)
        r = await client.post(f"/api/du-lieu/{d.key}/xoa", json={"ids": [rid], "ly_do": "dọn dữ liệu thử"}, headers=h)
        assert r.status_code == 200, (d.key, r.text)
        done.append(d.key)
    assert len(done) == len([d for d in DATASETS if d.them])
    # Chữ dài quá cột → báo lỗi nhập liệu (422), không lỗi máy chủ
    r = await client.post("/api/du-lieu/dan_cu", json={"data": {"ky": "2026-10", "chi_so": "nhan_khau", "gia_tri": "1", "nhom_tuoi": "x" * 30}}, headers=h)
    assert r.status_code == 422 and "tối đa 10" in r.json()["detail"]
