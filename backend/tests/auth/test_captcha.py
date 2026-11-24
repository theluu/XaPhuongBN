from app.auth import captcha
from app.core.config import get_settings
from tests.factories import PASSWORD, make_tenant, make_user


async def test_login_requires_captcha_when_configured(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "RECAPTCHA_SITE_KEY", "site-key")
    monkeypatch.setattr(s, "RECAPTCHA_SECRET", "secret")
    seen = []

    async def fake_verify(token, ip):  # noqa: ANN001, ANN202
        seen.append(token)
        return token == "ok"

    monkeypatch.setattr(captcha, "verify", fake_verify)
    t = await make_tenant()
    u = await make_user(t, "nguoi_xem")
    assert (await client.get("/api/auth/config")).json() == {"recaptcha_site_key": "site-key"}
    r = await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD})
    assert r.status_code == 400 and "người máy" in r.json()["detail"]
    r = await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD, "captcha": "bot"})
    assert r.status_code == 400
    r = await client.post("/api/auth/login", json={"username": u["username"], "password": PASSWORD, "captcha": "ok"})
    assert r.status_code == 200
    assert seen == ["bot", "ok"]


async def test_captcha_disabled_by_default(client):
    assert (await client.get("/api/auth/config")).json() == {"recaptcha_site_key": None}
