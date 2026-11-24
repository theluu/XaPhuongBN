"""Chống spam đăng nhập bằng Google reCAPTCHA v2 (hộp kiểm "Tôi không phải người máy").

Bật khi đặt RECAPTCHA_SITE_KEY và RECAPTCHA_SECRET. Không đặt (VD triển khai mạng nội bộ không có Internet)
thì bỏ qua, vẫn còn lớp khóa tài khoản sau nhiều lần sai mật khẩu.
"""
import httpx

from app.core.config import get_settings


def enabled() -> bool:
    s = get_settings()
    return bool(s.RECAPTCHA_SITE_KEY and s.RECAPTCHA_SECRET)


async def verify(token: str, ip: str | None) -> bool:
    s = get_settings()
    data = {"secret": s.RECAPTCHA_SECRET, "response": token}
    if ip:
        data["remoteip"] = ip
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.post(s.RECAPTCHA_VERIFY_URL, data=data)
            body = r.json()
    except (httpx.HTTPError, ValueError):
        return False
    if not body.get("success"):
        return False
    host = body.get("hostname")
    allowed = [h.strip() for h in s.RECAPTCHA_HOSTNAMES.split(",") if h.strip()]
    return not allowed or host in allowed
