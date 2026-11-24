"""Lệnh quản trị.

    python -m app.cli bootstrap
    python -m app.cli create-platform-admin <ten_dang_nhap> "<Họ tên>"   # tạo quản trị nền tảng đầu tiên (môi trường thật)
"""
import asyncio
import sys


async def create_platform_admin(username: str, ho_ten: str) -> dict:
    import pyotp
    from sqlalchemy import select

    from app.auth.models import Grant, User
    from app.auth.roles import default_grants
    from app.auth.security import hash_password, temp_password
    from app.core.db import admin_sessionmaker, import_models
    from app.platform.models import Tenant

    import_models()
    async with admin_sessionmaker()() as s:
        t = (await s.execute(select(Tenant).where(Tenant.cap == "nen_tang"))).scalars().first()
        if t is None:
            t = Tenant(ma_dvhc="NEN-TANG", ten="Nền tảng điều hành số xã/phường", cap="nen_tang", config={}, modules={})
            s.add(t)
            await s.flush()
        if (await s.execute(select(User.id).where(User.username == username))).scalar():
            raise SystemExit(f"Tên đăng nhập {username} đã tồn tại")
        pw, secret = temp_password(), pyotp.random_base32()
        u = User(tenant_id=t.id, username=username, ho_ten=ho_ten, chuc_danh="Quản trị nền tảng", don_vi="Nền tảng", trang_thai="hoat_dong",
                 password_hash=hash_password(pw), phai_doi_mat_khau=True, totp_secret=secret)
        s.add(u)
        await s.flush()
        for g_nhom, g_quyen in default_grants("quan_tri_nen_tang"):
            s.add(Grant(user_id=u.id, tenant_id=t.id, role="quan_tri_nen_tang", nhom_du_lieu=g_nhom, quyen=g_quyen))
        await s.commit()
    return {"username": username, "mat_khau_tam": pw, "totp_secret": secret,
            "otpauth_uri": pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="IOC-XP")}


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "bootstrap":
        from app.core.bootstrap import bootstrap

        asyncio.run(bootstrap())
        print("Đã khởi tạo CSDL")
    elif cmd == "create-platform-admin" and len(sys.argv) >= 4:
        out = asyncio.run(create_platform_admin(sys.argv[2], sys.argv[3]))
        print("Tài khoản:", out["username"])
        print("Mật khẩu tạm (đổi ở lần đăng nhập đầu):", out["mat_khau_tam"])
        print("Khóa xác thực 2 lớp (nhập vào ứng dụng xác thực):", out["totp_secret"])
        print("Hoặc URI:", out["otpauth_uri"])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
