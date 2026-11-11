from tests.factories import bearer, login, make_tenant, make_user

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def test_upload_and_download_own_tenant(client):
    t = await make_tenant()
    u = await make_user(t, "nhap_lieu", nhom=["cong_trinh"])
    tok = await login(client, u["username"])
    r = await client.post("/api/files", files={"file": ("a.png", PNG, "image/png")}, headers=bearer(tok))
    assert r.status_code == 201
    d = await client.get(f"/api/files/{r.json()['key']}", headers=bearer(tok))
    assert d.status_code == 200 and d.content == PNG


async def test_upload_rejects_disguised_file(client):
    t = await make_tenant()
    u = await make_user(t, "nhap_lieu", nhom=["cong_trinh"])
    tok = await login(client, u["username"])
    r = await client.post("/api/files", files={"file": ("a.png", b"<script>alert(1)</script>", "image/png")}, headers=bearer(tok))
    assert r.status_code == 422
    r = await client.post("/api/files", files={"file": ("a.exe", b"MZ\x90\x00", "application/octet-stream")}, headers=bearer(tok))
    assert r.status_code == 422


async def test_cannot_download_other_tenant_file(client):
    a, b = await make_tenant(), await make_tenant()
    ua, ub = await make_user(a, "nhap_lieu", nhom=["ktxh"]), await make_user(b, "lanh_dao")
    key = (await client.post("/api/files", files={"file": ("a.png", PNG, "image/png")},
                             headers=bearer(await login(client, ua["username"])))).json()["key"]
    r = await client.get(f"/api/files/{key}", headers=bearer(await login(client, ub["username"])))
    assert r.status_code == 404
