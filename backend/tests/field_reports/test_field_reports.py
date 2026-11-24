from datetime import date, timedelta

from app.core.db import admin_sessionmaker
from app.platform.models import ResidentialGroup
from tests.factories import bearer, login, make_tenant, make_user


async def _setup(client):  # noqa: ANN001
    t = await make_tenant(cap="phuong")
    async with admin_sessionmaker()() as s:
        g = ResidentialGroup(tenant_id=t, ma_tdp="TDP01", ten="Tổ dân phố số 1", loai="tdp")
        s.add(g)
        await s.commit()
        gid = g.id
    canbo = await make_user(t, "nhap_lieu", ["tthc_pakn"])
    lanh_dao = await make_user(t, "lanh_dao")
    tv = await make_user(t, "man_hinh_tv")
    xem = await make_user(t, "nguoi_xem")
    return t, gid, {k: bearer(await login(client, u["username"])) for k, u in
                    {"canbo": canbo, "lanh_dao": lanh_dao, "tv": tv, "xem": xem}.items()}


async def test_full_flow_receive_locate_assign_track_confirm(client):
    t, gid, h = await _setup(client)
    body = {"tieu_de": "Rác tồn đọng đầu ngõ", "linh_vuc": "moi_truong", "nguon": "duong_day_nong", "tdp_id": gid,
            "dia_chi": "Ngõ 5", "nguoi_gui_ten": "Nguyễn Văn A", "nguoi_gui_sdt": "0912345678"}
    r = await client.post("/api/phan-anh", json=body, headers=h["canbo"])
    assert r.status_code == 201, r.text
    pa = r.json()
    assert pa["ma"].startswith(f"PA-{date.today().year}-") and pa["trang_thai"] == "moi" and pa["co_vi_tri"] is False
    assert pa["don_vi_phu_trach"] == "KTHTDT"  # phường: Phòng Kinh tế, Hạ tầng và Đô thị chủ trì môi trường
    assert pa["nguoi_gui_ten"] == "Nguyễn Văn A"
    rid = pa["id"]

    # Cán bộ nhập liệu không được giao việc
    assert (await client.post(f"/api/phan-anh/{rid}/giao", json={"don_vi_phu_trach": "KTHTDT", "han_xu_ly": date.today().isoformat()},
                              headers=h["canbo"])).status_code == 403
    r = await client.patch(f"/api/phan-anh/{rid}/vi-tri", json={"lat": 21.27, "lng": 106.1}, headers=h["canbo"])
    assert r.json()["co_vi_tri"] is True
    assert (await client.patch(f"/api/phan-anh/{rid}/vi-tri", json={"lat": 1, "lng": 1}, headers=h["canbo"])).status_code == 422

    han = (date.today() + timedelta(days=2)).isoformat()
    r = await client.post(f"/api/phan-anh/{rid}/giao", json={"don_vi_phu_trach": "KTHTDT", "nguoi_phu_trach": "Trần B", "han_xu_ly": han, "chi_dao": "Xử lý ngay"},
                          headers=h["lanh_dao"])
    assert r.status_code == 200 and r.json()["trang_thai"] == "da_giao"
    assert "nguoi_gui_ten" not in r.json()  # lãnh đạo chỉ có quyền đọc nhóm tthc_pakn → không thấy người gửi

    r = await client.post(f"/api/phan-anh/{rid}/tien-do", json={"tien_do_pct": 40, "ghi_chu": "Đã kiểm tra hiện trường"}, headers=h["canbo"])
    assert r.json()["trang_thai"] == "dang_xu_ly" and r.json()["tien_do_pct"] == 40
    assert (await client.post(f"/api/phan-anh/{rid}/tien-do", json={"bao_cao_hoan_thanh": True}, headers=h["canbo"])).status_code == 422
    r = await client.post(f"/api/phan-anh/{rid}/tien-do", json={"bao_cao_hoan_thanh": True, "ket_qua": "Đã thu gom"}, headers=h["canbo"])
    assert r.json()["trang_thai"] == "cho_xac_nhan"
    assert (await client.post(f"/api/phan-anh/{rid}/xac-nhan", json={"dong_y": False}, headers=h["lanh_dao"])).status_code == 422
    r = await client.post(f"/api/phan-anh/{rid}/xac-nhan", json={"dong_y": True}, headers=h["lanh_dao"])
    assert r.json()["trang_thai"] == "hoan_thanh"
    steps = [x["hanh_dong"] for x in r.json()["lich_su"]]
    assert steps == ["tiep_nhan", "xac_dinh_vi_tri", "giao_xu_ly", "cap_nhat_tien_do", "bao_cao_hoan_thanh", "xac_nhan_hoan_thanh"]


async def test_overview_counts_filters_and_tv_hides_sender(client):
    t, gid, h = await _setup(client)
    ids = []
    for ten, khan in [("Cây đổ chắn đường", True), ("Đèn hỏng", False), ("Hố ga vỡ", False)]:
        r = await client.post("/api/phan-anh", json={"tieu_de": ten, "linh_vuc": "ha_tang", "khan_cap": khan, "dia_chi": "Đường A",
                                                     "nguoi_gui_ten": "Bí Mật", "lat": 21.27, "lng": 106.1}, headers=h["canbo"])
        ids.append(r.json()["id"])
    today = date.today()
    from app.core.db import tenant_session
    from app.field_reports.models import FieldReport

    async with tenant_session([t]) as s:
        r = await s.get(FieldReport, ids[1])
        r.han_xu_ly, r.trang_thai = today - timedelta(days=3), "da_giao"
        r2 = await s.get(FieldReport, ids[2])
        r2.han_xu_ly, r2.trang_thai = today, "da_giao"
        await s.commit()
    ov = (await client.get("/api/dieu-hanh/tong-quan", headers=h["lanh_dao"])).json()
    assert ov["chi_so"]["phan_anh_moi"] == 1 and ov["chi_so"]["qua_han"] == 1 and ov["chi_so"]["den_han_hom_nay"] == 1
    assert ov["viec"][0]["ten"] == "Cây đổ chắn đường"  # khẩn cấp lên đầu
    assert ov["viec"][1]["qua_han_ngay"] == 3
    qh = (await client.get("/api/dieu-hanh/tong-quan", params={"loc": "qua_han"}, headers=h["lanh_dao"])).json()
    assert [x["ten"] for x in qh["viec"]] == ["Đèn hỏng"] and qh["viec"][0]["don_vi"]
    tv = (await client.get("/api/dieu-hanh/tong-quan", params={"che_do": "tv"}, headers=h["tv"])).json()
    assert len(tv["viec"]) <= 5 and "Bí Mật" not in str(tv)
    detail = (await client.get(f"/api/phan-anh/{ids[0]}", headers=h["tv"])).json()
    assert "nguoi_gui_ten" not in detail
    # Người xem thông thường không đọc được nhóm nhạy cảm tthc_pakn
    assert (await client.get("/api/phan-anh", headers=h["xem"])).status_code == 403
    assert (await client.get("/api/dieu-hanh/tong-quan", headers=h["xem"])).json()["chi_so"]["phan_anh_moi"] == 0


async def test_report_validation_and_isolation(client):
    t, gid, h = await _setup(client)
    assert (await client.post("/api/phan-anh", json={"tieu_de": "Thiếu địa điểm", "linh_vuc": "ha_tang"}, headers=h["canbo"])).status_code == 422
    assert (await client.post("/api/phan-anh", json={"tieu_de": "Sai lĩnh vực", "linh_vuc": "khong_co", "dia_chi": "A"}, headers=h["canbo"])).status_code == 422
    r = await client.post("/api/phan-anh", json={"tieu_de": "Hợp lệ", "linh_vuc": "an_ninh", "dia_chi": "A"}, headers=h["canbo"])
    assert r.json()["don_vi_phu_trach"] == "CA"
    other = await make_tenant()
    o = await make_user(other, "lanh_dao")
    oh = bearer(await login(client, o["username"]))
    assert (await client.get(f"/api/phan-anh/{r.json()['id']}", headers=oh)).status_code == 404


async def test_catalogs_follow_commune_structure(client):
    t = await make_tenant(cap="xa")
    u = await make_user(t, "lanh_dao")
    d = (await client.get("/api/dieu-hanh/danh-muc", headers=bearer(await login(client, u["username"])))).json()
    assert d["dia_ban_label"] == "Thôn"
    ten = [p["ten"] for p in d["phong_ban"]]
    assert "Phòng Kinh tế" in ten and "Văn phòng HĐND và UBND" in ten and "Phòng Văn hóa – Xã hội" in ten and "Công an xã" in ten


async def test_my_work_filter_by_linked_staff(client):
    from app.core.db import tenant_session as ts
    from app.org.models import Staff

    t, gid, h = await _setup(client)
    canbo2 = await make_user(t, "nhap_lieu", ["tthc_pakn"])
    hb = bearer(await login(client, canbo2["username"]))
    await client.get("/api/co-cau", headers=hb)  # tạo cơ cấu mặc định
    async with ts([t]) as s:
        s.add(Staff(tenant_id=t, ma="KT9", don_vi_ma="VHXH", ho_ten="Cán Bộ Xã Hội", chuc_vu="Chuyên viên", user_id=canbo2["id"], linh_vuc=[], dia_ban_ids=[]))
        await s.commit()
    ids = {}
    for ten, lv in [("Hộ nghèo cần hỗ trợ", "an_sinh"), ("Đèn hỏng", "ha_tang")]:
        ids[ten] = (await client.post("/api/phan-anh", json={"tieu_de": ten, "linh_vuc": lv, "dia_chi": "A"}, headers=h["canbo"])).json()["id"]
    han = (date.today() + timedelta(days=3)).isoformat()
    await client.post(f"/api/phan-anh/{ids['Hộ nghèo cần hỗ trợ']}/giao", json={"don_vi_phu_trach": "VHXH", "han_xu_ly": han}, headers=h["lanh_dao"])
    await client.post(f"/api/phan-anh/{ids['Đèn hỏng']}/giao", json={"don_vi_phu_trach": "KTHTDT", "nguoi_phu_trach": "Cán Bộ Xã Hội", "han_xu_ly": han}, headers=h["lanh_dao"])
    all_ = (await client.get("/api/dieu-hanh/tong-quan", headers=hb)).json()
    mine = (await client.get("/api/dieu-hanh/tong-quan", params={"pham_vi": "cua_toi"}, headers=hb)).json()
    assert {x["ten"] for x in mine["viec"]} == {"Hộ nghèo cần hỗ trợ", "Đèn hỏng"}  # việc của phòng mình + việc giao đích danh
    assert mine["toi"]["don_vi_ten"] == "Phòng Văn hóa – Xã hội" and len(all_["viec"]) >= len(mine["viec"])
    assert (await client.get("/api/dieu-hanh/tong-quan", params={"pham_vi": "x"}, headers=hb)).status_code == 422
