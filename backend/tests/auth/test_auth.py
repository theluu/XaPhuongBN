import io

import pyotp
from fastapi import Depends
from openpyxl import Workbook
from sqlalchemy import select

from app.auth.deps import require
from app.auth.models import User
from app.core.config import get_settings
from app.core.db import admin_sessionmaker
from tests.factories import PASSWORD, bearer, login, make_tenant, make_user


async def test_login_ok(client):
    t = await make_tenant()
    u = await make_user(t, "lanh_dao")
    r = await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD})
    assert r.status_code == 200
    tok = r.json()["access_token"]
    me = await client.get("/api/auth/me", headers=bearer(tok))
    assert me.status_code == 200
    assert me.json()["username"] == u["username"]
    assert me.json()["tenant_id"] == t


async def test_wrong_password_generic_message(client):
    t = await make_tenant()
    u = await make_user(t)
    r = await client.post("/api/auth/login", json={"username": u["username"], "password": "sai"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Sai tên đăng nhập hoặc mật khẩu"
    r = await client.post("/api/auth/login", json={"username": "khong_ton_tai", "password": "sai"})
    assert r.json()["detail"] == "Sai tên đăng nhập hoặc mật khẩu"


async def test_lockout_after_5_failures(client):
    t = await make_tenant()
    u = await make_user(t)
    for _ in range(5):
        await client.post("/api/auth/login", json={"username": u["username"], "password": "sai"})
    r = await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD})
    assert r.status_code == 423
    assert r.json()["detail"] == "Tài khoản tạm khóa 15 phút"


async def test_2fa_required_when_enabled(client):
    s = get_settings()
    s.REQUIRE_2FA = True
    try:
        t = await make_tenant()
        secret = pyotp.random_base32()
        u = await make_user(t, "lanh_dao", totp_secret=secret)
        r = await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD})
        assert r.status_code == 401
        assert r.json()["detail"] == "Cần mã xác thực 2 lớp"
        r = await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD, "otp": "000000"})
        assert r.status_code == 401
        await login(client, u["username"], otp=pyotp.TOTP(secret).now())
        # cán bộ nhập liệu không bắt buộc 2FA
        n = await make_user(t, "nhap_lieu", nhom=["ktxh"])
        await login(client, n["username"])
    finally:
        s.REQUIRE_2FA = False


def _probe_app(client, quyen: str, nhom: str):
    app = client._transport.app  # type: ignore[attr-defined]

    path = f"/api/_probe/{quyen}/{nhom}"
    if not any(getattr(r, "path", None) == path for r in app.routes):
        async def probe(user=Depends(require(quyen, nhom))):
            return {"ok": True}
        app.add_api_route(path, probe, methods=["POST"])
    return path


async def test_doc_without_nhap_cannot_post(client):
    t = await make_tenant()
    viewer = await make_user(t, "nguoi_xem")
    tok = await login(client, viewer["username"])
    r = await client.post(_probe_app(client, "nhap", "ktxh"), headers=bearer(tok))
    assert r.status_code == 403


async def test_nhap_without_duyet_cannot_confirm(client):
    t = await make_tenant()
    staff = await make_user(t, "nhap_lieu", nhom=["ktxh"])
    tok = await login(client, staff["username"])
    assert (await client.post(_probe_app(client, "nhap", "ktxh"), headers=bearer(tok))).status_code == 200
    assert (await client.post(_probe_app(client, "duyet", "ktxh"), headers=bearer(tok))).status_code == 403


async def test_platform_admin_cannot_read_budget(client):
    platform = await make_tenant("Nền tảng", cap="nen_tang")
    admin = await make_user(platform, "quan_tri_nen_tang")
    tok = await login(client, admin["username"])
    assert (await client.post(_probe_app(client, "doc", "ngan_sach"), headers=bearer(tok))).status_code == 403
    assert (await client.post(_probe_app(client, "doc", "dan_cu"), headers=bearer(tok))).status_code == 403


async def test_nguoi_xem_cannot_read_sensitive(client):
    t = await make_tenant()
    viewer = await make_user(t, "nguoi_xem")
    tok = await login(client, viewer["username"])
    assert (await client.post(_probe_app(client, "doc", "ktxh"), headers=bearer(tok))).status_code == 200
    assert (await client.post(_probe_app(client, "doc", "ngan_sach"), headers=bearer(tok))).status_code == 403


async def test_revoke_access_immediately_invalidates_token(client):
    t = await make_tenant()
    admin = await make_user(t, "quan_tri_don_vi")
    victim = await make_user(t, "lanh_dao")
    a_tok = await login(client, admin["username"])
    v_tok = await login(client, victim["username"])
    assert (await client.get("/api/auth/me", headers=bearer(v_tok))).status_code == 200
    r = await client.post(f"/api/users/{victim['id']}/revoke", json={"ly_do": "Chuyển công tác"}, headers=bearer(a_tok))
    assert r.status_code == 200
    assert (await client.get("/api/auth/me", headers=bearer(v_tok))).status_code == 401
    r = await client.post("/api/auth/login", json={"username": victim["username"], "password": PASSWORD})
    assert r.status_code == 401


async def test_cannot_revoke_user_of_other_tenant(client):
    t1, t2 = await make_tenant(), await make_tenant()
    admin = await make_user(t1, "quan_tri_don_vi")
    other = await make_user(t2, "lanh_dao")
    tok = await login(client, admin["username"])
    r = await client.post(f"/api/users/{other['id']}/revoke", json={"ly_do": "x"}, headers=bearer(tok))
    assert r.status_code == 404


def _xlsx(rows: list[list[str]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Tên đăng nhập", "Họ tên", "Đơn vị", "Chức danh", "Email", "Vai trò", "Nhóm dữ liệu", "Phạm vi khai thác", "Người phê duyệt"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def test_user_import_requires_approver(client):
    t = await make_tenant()
    admin = await make_user(t, "quan_tri_don_vi")
    tok = await login(client, admin["username"])
    data = _xlsx([
        ["canbo_a1", "Nguyễn Văn A", "Văn phòng", "Chuyên viên", "a@x.vn", "nhap_lieu", "ktxh", "Chỉ tiêu KT-XH", admin["username"]],
        ["canbo_b1", "Trần Thị B", "Văn phòng", "Chuyên viên", "b@x.vn", "nhap_lieu", "ktxh", "Chỉ tiêu KT-XH", ""],
    ])
    files = {"file": ("tai_khoan.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = await client.post("/api/users/import", files=files, headers=bearer(tok))
    assert r.status_code == 422
    loi = r.json()["detail"]["loi"]
    assert {"dong": 3, "cot": "Người phê duyệt", "thong_bao": "Bắt buộc ghi người phê duyệt"} in loi
    async with admin_sessionmaker()() as s:
        assert (await s.execute(select(User).where(User.username == "canbo_a1"))).scalar() is None


async def test_user_import_then_approve(client):
    t = await make_tenant()
    admin = await make_user(t, "quan_tri_don_vi")
    tok = await login(client, admin["username"])
    name = f"canbo_{admin['id']}"
    data = _xlsx([[name, "Lê Văn C", "Địa chính", "Công chức", "c@x.vn", "nhap_lieu", "cong_trinh", "Công trình", admin["username"]]])
    files = {"file": ("tk.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = await client.post("/api/users/import", files=files, headers=bearer(tok))
    assert r.status_code == 200, r.text
    new_id = r.json()["tao_moi"][0]["id"]
    r = await client.post("/api/auth/login", json={"username": name, "password": "x"})
    assert r.status_code == 401
    r = await client.post(f"/api/users/{new_id}/approve", headers=bearer(tok))
    assert r.status_code == 200
    temp = r.json()["mat_khau_tam"]
    r = await client.post("/api/auth/login", json={"username": name, "password": temp})
    assert r.status_code == 200
    assert r.json()["user"]["phai_doi_mat_khau"] is True
