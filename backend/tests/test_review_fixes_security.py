"""Kiểm thử cho các phát hiện của lượt review cuối (C1, C2, I1–I4)."""
import io

import pyotp
from openpyxl import Workbook
from sqlalchemy import select

from app.auth.models import User
from app.core.config import get_settings
from app.core.db import admin_sessionmaker
from seeds.run import seed_platform
from tests.factories import PASSWORD, bearer, login, make_tenant, make_user, uid


async def _unit_admin(client):  # noqa: ANN001
    t = await make_tenant()
    u = await make_user(t, "quan_tri_don_vi")
    return t, bearer(await login(client, u["username"]))


# ---------- C1: leo thang quyền ----------
async def test_c1_unit_admin_cannot_grant_system_or_wildcard_groups(client):
    t, h = await _unit_admin(client)
    for nhom in (["he_thong"], ["*"], ["quan_tri"], ["ktxh", "he_thong"]):
        r = await client.post("/api/admin/users", json={"username": uid("x"), "ho_ten": "X", "role": "chuyen_nganh", "nhom": nhom}, headers=h)
        assert r.status_code == 422, (nhom, r.text)


async def test_c1_import_cannot_create_platform_admin(client):
    t, h = await _unit_admin(client)
    wb = Workbook()
    ws = wb.active
    ws.append(["Tên đăng nhập", "Họ tên", "Đơn vị", "Chức danh", "Email", "Vai trò", "Nhóm dữ liệu", "Phạm vi khai thác", "Người phê duyệt"])
    ws.append([uid("evil"), "Evil", "X", "X", "", "quan_tri_nen_tang", "", "", "qt"])
    ws.append([uid("evil2"), "Evil2", "X", "X", "", "chuyen_nganh", "he_thong", "", "qt"])
    b = io.BytesIO()
    wb.save(b)
    r = await client.post("/api/users/import", files={"file": ("u.xlsx", b.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, headers=h)
    assert r.status_code == 422
    msgs = " ".join(e["thong_bao"] for e in r.json()["detail"]["loi"])
    assert "quan_tri_nen_tang" in msgs and "Nhóm dữ liệu không hợp lệ" in msgs


async def test_c1_leader_account_created_by_unit_admin_needs_leader_approval(client):
    t, h = await _unit_admin(client)
    r = await client.post("/api/admin/users", json={"username": uid("ld"), "ho_ten": "Lãnh đạo mới", "role": "lanh_dao"}, headers=h)
    assert r.status_code == 201 and r.json()["trang_thai"] == "cho_duyet" and r.json()["mat_khau_tam"] is None
    new_id = r.json()["id"]
    assert (await client.post(f"/api/users/{new_id}/approve", headers=h)).status_code == 403
    boss = await make_user(t, "lanh_dao")
    r = await client.post(f"/api/users/{new_id}/approve", headers=bearer(await login(client, boss["username"])))
    assert r.status_code == 200 and r.json()["mat_khau_tam"]


async def test_c1_leader_reads_business_groups_not_system(client):
    t = await make_tenant()
    u = await make_user(t, "lanh_dao")
    me = (await client.get("/api/auth/me", headers=bearer(await login(client, u["username"])))).json()
    assert "*" not in me["quyen"] and "he_thong" not in me["quyen"] and "ngan_sach" in me["quyen"]


# ---------- C2: môi trường thật đăng nhập được ----------
async def test_c2_onboard_returns_totp_and_leader_can_login_with_2fa(client):
    await seed_platform()
    p = await make_tenant("Nền tảng", cap="nen_tang")
    a = await make_user(p, "quan_tri_nen_tang")
    h = bearer(await login(client, a["username"]))
    name = uid("ct")
    r = await client.post("/api/platform/onboard", json={"ma_dvhc": uid("P"), "ten": "Phường Mới", "cap": "phuong", "pack": "phuong_do_thi", "so_tdp": 1,
                                                          "lanh_dao": {"username": name, "ho_ten": "A", "chuc_danh": "Chủ tịch"}}, headers=h)
    j = r.json()
    assert j["totp_secret"]
    s = get_settings()
    s.REQUIRE_2FA = True
    try:
        r = await client.post("/api/auth/login", json={"username": name, "password": j["mat_khau_tam"], "otp": pyotp.TOTP(j["totp_secret"]).now()})
        assert r.status_code == 200
    finally:
        s.REQUIRE_2FA = False


async def test_c2_cli_creates_first_platform_admin():
    from app.cli import create_platform_admin

    name = uid("root")
    out = await create_platform_admin(name, "Quản trị nền tảng")
    assert out["mat_khau_tam"] and out["totp_secret"]
    async with admin_sessionmaker()() as s:
        u = (await s.execute(select(User).where(User.username == name))).scalar_one()
    assert u.totp_secret and u.trang_thai == "hoat_dong" and u.phai_doi_mat_khau


# ---------- I1: thử mã OTP bị tính vào khóa tài khoản, mã không dùng lại ----------
async def test_i1_wrong_otp_counts_toward_lockout_and_codes_not_reusable(client):
    s = get_settings()
    s.REQUIRE_2FA = True
    try:
        t = await make_tenant()
        secret = pyotp.random_base32()
        u = await make_user(t, "lanh_dao", totp_secret=secret)
        code = pyotp.TOTP(secret).now()
        assert (await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD, "otp": code})).status_code == 200
        r = await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD, "otp": code})
        assert r.status_code == 401  # không dùng lại mã đã dùng
        u2 = await make_user(t, "lanh_dao", totp_secret=secret)
        for _ in range(5):
            await client.post("/api/auth/login", json={"username": u2["username"], "password": PASSWORD, "otp": "000000"})
        r = await client.post("/api/auth/login", json={"username": u2["username"], "password": PASSWORD, "otp": pyotp.TOTP(secret).now()})
        assert r.status_code == 423
    finally:
        s.REQUIRE_2FA = False


# ---------- I2: bắt buộc đổi mật khẩu ở phía máy chủ ----------
async def test_i2_temporary_password_blocks_api_until_changed(client):
    t, h = await _unit_admin(client)
    name = uid("nv")
    r = await client.post("/api/admin/users", json={"username": name, "ho_ten": "NV", "role": "nhap_lieu", "nhom": ["ktxh"]}, headers=h)
    pw = r.json()["mat_khau_tam"]
    tok = bearer((await client.post("/api/auth/login", json={"username": name, "password": pw})).json()["access_token"])
    assert (await client.get("/api/auth/me", headers=tok)).status_code == 200
    assert (await client.get("/api/tenant", headers=tok)).status_code == 200
    r = await client.get("/api/indicators", headers=tok)
    assert r.status_code == 403 and r.json()["detail"] == "Cần đổi mật khẩu tạm trước khi sử dụng hệ thống"


# ---------- I4: quyền tách theo từng đơn vị ----------
async def test_i4_permissions_are_per_tenant(client):
    a, b = await make_tenant(), await make_tenant()
    u = await make_user(None, "chuyen_nganh", nhom=["gd_yt_mt"],
                        extra_grants=[(a, "chuyen_nganh", ["ngan_sach"], ["doc", "nhap", "duyet"]), (b, "chuyen_nganh", ["gd_yt_mt"], ["doc", "nhap", "duyet"])])
    h = bearer(await login(client, u["username"]))
    assert (await client.get("/api/budget/summary", params={"tenant": a, "ky": "2026-10"}, headers=h)).status_code == 200
    assert (await client.get("/api/budget/summary", params={"tenant": b, "ky": "2026-10"}, headers=h)).status_code == 403
