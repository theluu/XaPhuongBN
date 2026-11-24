from datetime import date, timedelta

from app.core.db import tenant_session
from app.field_reports.models import FieldReport
from tests.factories import bearer, login, make_tenant, make_user


async def test_default_structure_follows_two_level_model(client):
    t = await make_tenant("Xã An Lạc", cap="xa")
    u = await make_user(t, "nguoi_xem")
    d = (await client.get("/api/co-cau", headers=bearer(await login(client, u["username"])))).json()
    ten = {x["ma"]: x["ten"] for x in d["don_vi"]}
    assert ten["UBND"] == "Ủy ban nhân dân xã An Lạc" and ten["DU"] == "Đảng ủy xã An Lạc"
    assert ten["KT"] == "Phòng Kinh tế" and ten["VP"] == "Văn phòng HĐND và UBND" and ten["VHXH"] == "Phòng Văn hóa – Xã hội"
    assert "HND" in ten  # xã có Hội Nông dân
    assert next(x for x in d["don_vi"] if x["ma"] == "HLHPN")["cap_tren_ma"] == "MTTQ"
    assert d["dia_ban_label"] == "Thôn"


async def test_staff_crud_contacts_and_workload(client):
    t = await make_tenant("Phường Đông", cap="phuong")
    admin = bearer(await login(client, (await make_user(t, "quan_tri_don_vi"))["username"]))
    ld = bearer(await login(client, (await make_user(t, "lanh_dao"))["username"]))
    tv = bearer(await login(client, (await make_user(t, "man_hinh_tv"))["username"]))
    await client.get("/api/co-cau", headers=admin)
    body = {"ma": "TP1", "don_vi_ma": "KTHTDT", "ho_ten": "Nguyễn Văn An", "chuc_vu": "Trưởng phòng", "cap": "truong", "dien_thoai": "0900000001",
            "nhiem_vu": "Hạ tầng", "linh_vuc": ["ha_tang"]}
    r = await client.post("/api/co-cau/can-bo", json=body, headers=admin)
    assert r.status_code == 201, r.text
    assert (await client.post("/api/co-cau/can-bo", json=body, headers=admin)).status_code == 409
    assert (await client.post("/api/co-cau/can-bo", json={**body, "ma": "X", "don_vi_ma": "KHONG"}, headers=admin)).status_code == 422
    assert (await client.post("/api/co-cau/can-bo", json={**body, "ma": "Y"}, headers=ld)).status_code == 403
    async with tenant_session([t]) as s:
        s.add(FieldReport(tenant_id=t, ma="PA-1", tieu_de="Đèn hỏng", linh_vuc="ha_tang", don_vi_phu_trach="KTHTDT", nguoi_phu_trach="Nguyễn Văn An",
                          han_xu_ly=date.today() - timedelta(days=2), trang_thai="dang_xu_ly", lich_su=[], anh_keys=[], anh_ket_qua_keys=[]))
        await s.commit()
    d = (await client.get("/api/co-cau", headers=ld)).json()
    kt = next(x for x in d["don_vi"] if x["ma"] == "KTHTDT")
    assert kt["khoi_luong"]["dang_xu_ly"] == 1 and kt["khoi_luong"]["qua_han"] == 1
    an = next(x for x in d["can_bo"] if x["ma"] == "TP1")
    assert an["khoi_luong"]["viec"][0]["ten"] == "Đèn hỏng" and an["dien_thoai"] == "0900000001"
    d = (await client.get("/api/co-cau", headers=tv)).json()
    assert next(x for x in d["can_bo"] if x["ma"] == "TP1")["dien_thoai"] is None  # TV không hiện số điện thoại


async def test_unit_tree_rules(client):
    t = await make_tenant(cap="phuong")
    admin = bearer(await login(client, (await make_user(t, "quan_tri_don_vi"))["username"]))
    await client.get("/api/co-cau", headers=admin)
    unit = {"ma": "TO1", "ten": "Tổ công tác chuyển đổi số", "khoi": "chuyen_mon", "cap_tren_ma": "VP"}
    assert (await client.post("/api/co-cau/don-vi", json=unit, headers=admin)).status_code == 201
    assert (await client.put("/api/co-cau/don-vi/VP", json={"ma": "VP", "ten": "Văn phòng", "khoi": "chuyen_mon", "cap_tren_ma": "TO1"}, headers=admin)).status_code == 422
    assert (await client.delete("/api/co-cau/don-vi/VP", headers=admin)).status_code == 409  # còn đơn vị cấp dưới
    assert (await client.delete("/api/co-cau/don-vi/TO1", headers=admin)).status_code == 200
