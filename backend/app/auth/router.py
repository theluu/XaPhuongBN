import io
from datetime import UTC, datetime, timedelta

import pyotp
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from openpyxl import load_workbook
from pydantic import BaseModel
from sqlalchemy import select

from app.audit.middleware import client_ip
from app.audit.service import record, record_change
from app.auth.deps import get_current_user, require
from app.auth.models import Grant, User
from app.auth.roles import NEED_LEADER_APPROVAL, ROLES, ROLES_2FA, UNIT_CREATABLE, default_grants
from app.auth.security import hash_password, make_token, temp_password, verify_password
from app.core.config import get_settings
from app.core.db import admin_sessionmaker
from app.core.principal import CurrentUser

router = APIRouter(prefix="/api", tags=["xac-thuc"])


def otp_step(secret: str, code: str, last: int | None) -> int | None:
    """Trả về bước thời gian của mã hợp lệ (±1 bước), từ chối mã đã dùng."""
    import hmac
    import time

    totp = pyotp.TOTP(secret)
    now = int(time.time() // 30)
    for st in (now - 1, now, now + 1):
        if hmac.compare_digest(totp.at(st * 30), str(code).strip()) and st > (last or 0):
            return st
    return None
BAD_LOGIN = "Sai tên đăng nhập hoặc mật khẩu"


class LoginIn(BaseModel):
    username: str
    password: str
    otp: str | None = None
    captcha: str | None = None


def user_out(u: User, p: CurrentUser | None = None) -> dict:
    return {
        "id": u.id, "username": u.username, "ho_ten": u.ho_ten, "don_vi": u.don_vi, "chuc_danh": u.chuc_danh,
        "tenant_id": p.tenant_id if p and p.dai_dien else u.tenant_id, "phai_doi_mat_khau": u.phai_doi_mat_khau,
        "dai_dien": bool(p and p.dai_dien),
        "roles": sorted(p.roles) if p else [],
        "quyen": {k: sorted(v) for k, v in p.permissions.items()} if p else {},
    }


@router.get("/auth/config")
async def auth_config() -> dict:
    """Cấu hình công khai cho trang đăng nhập."""
    from app.auth import captcha

    return {"recaptcha_site_key": get_settings().RECAPTCHA_SITE_KEY if captcha.enabled() else None}


CAPTCHA_MISSING = "Vui lòng đánh dấu ô “Tôi không phải người máy”"
CAPTCHA_BAD = "Xác minh chống spam không thành công, vui lòng thử lại"


@router.post("/auth/login")
async def login(body: LoginIn, request: Request) -> dict:
    from app.auth import captcha

    s_ = get_settings()
    now = datetime.now(UTC)
    status, detail, user_id, tenant_id = 401, BAD_LOGIN, None, None
    try:
        if captcha.enabled():
            if not body.captcha:
                status = 400
                raise HTTPException(400, CAPTCHA_MISSING)
            if not await captcha.verify(body.captcha, client_ip(request)):
                status = 400
                raise HTTPException(400, CAPTCHA_BAD)
        async with admin_sessionmaker()() as s:
            u = (await s.execute(select(User).where(User.username == body.username))).scalar()
            if u is None:
                verify_password(body.password, None)
                raise HTTPException(401, BAD_LOGIN)
            user_id, tenant_id = u.id, u.tenant_id
            if u.locked_until and u.locked_until > now:
                status = 423
                raise HTTPException(423, f"Tài khoản tạm khóa {s_.LOCKOUT_MINUTES} phút")
            async def fail(msg: str) -> None:
                u.failed_count += 1
                if u.failed_count >= s_.LOCKOUT_THRESHOLD:
                    u.locked_until = now + timedelta(minutes=s_.LOCKOUT_MINUTES)
                    u.failed_count = 0
                await s.commit()
                raise HTTPException(401, msg)

            if u.trang_thai != "hoat_dong" or not verify_password(body.password, u.password_hash):
                await fail(BAD_LOGIN)
            if u.tenant_id is not None:  # trên tên miền riêng của một phường: chỉ cán bộ phường đó (và quản trị nền tảng) đăng nhập được
                from app.cong_khai.router import request_host
                from app.cong_khai.service import tenant_for_host
                from app.platform.models import Tenant

                host_t = await tenant_for_host(s, request_host(request))
                own = await s.get(Tenant, u.tenant_id)
                if host_t is not None and host_t.id != u.tenant_id and (own is None or own.cap != "nen_tang"):
                    await fail(BAD_LOGIN)
            if u.tenant_id is not None:
                from app.platform.models import Tenant

                t = await s.get(Tenant, u.tenant_id)
                if t is not None and t.trang_thai != "hoat_dong":
                    status = 403
                    raise HTTPException(403, "Đơn vị đang tạm dừng sử dụng hệ thống, liên hệ quản trị nền tảng")
            roles = set((await s.execute(select(Grant.role).where(Grant.user_id == u.id))).scalars())
            if s_.REQUIRE_2FA and roles & ROLES_2FA:
                if not u.totp_secret:
                    raise HTTPException(403, "Tài khoản chưa thiết lập xác thực 2 lớp, liên hệ quản trị đơn vị")
                if not body.otp:
                    raise HTTPException(401, "Cần mã xác thực 2 lớp")
                step = otp_step(u.totp_secret, body.otp, u.totp_last)
                if step is None:
                    await fail("Mã xác thực không đúng hoặc đã được dùng")
                u.totp_last = step
            u.failed_count = 0
            u.locked_until = None
            await s.commit()
            from app.auth.deps import build_principal

            principal = await build_principal(u)
            status, detail = 200, "ok"
            return {"access_token": make_token(u.id, u.token_version), "token_type": "bearer", "user": user_out(u, principal)}
    except HTTPException as e:
        status, detail = e.status_code, e.detail
        raise
    finally:
        await record(method="POST", path="/api/auth/login", status=status, user_id=user_id, tenant_id=tenant_id,
                     ip=client_ip(request), doi_tuong=f"dang_nhap:{body.username}", after={"ket_qua": detail})


@router.get("/auth/me")
async def me(user: CurrentUser = Depends(get_current_user)) -> dict:
    async with admin_sessionmaker()() as s:
        u = await s.get(User, user.id)
    assert u is not None
    return user_out(u, user)


async def _own_user(s, actor: CurrentUser, user_id: int) -> User:  # noqa: ANN001
    u = await s.get(User, user_id)
    if u is None or (actor.tenant_id is not None and u.tenant_id != actor.tenant_id):
        raise HTTPException(404, "Không tìm thấy người dùng")
    return u


class RevokeIn(BaseModel):
    ly_do: str


@router.post("/users/{user_id}/revoke", tags=["nguoi-dung"])
async def revoke(user_id: int, body: RevokeIn, actor: CurrentUser = Depends(require("duyet", "quan_tri"))) -> dict:
    if not body.ly_do.strip():
        raise HTTPException(422, "Cần ghi lý do thu hồi quyền")
    async with admin_sessionmaker()() as s:
        u = await _own_user(s, actor, user_id)
        before = {"trang_thai": u.trang_thai}
        u.trang_thai = "thu_hoi"
        u.token_version += 1
        u.ly_do_thu_hoi = body.ly_do
        await s.commit()
    await record_change(actor, u.tenant_id, f"nguoi_dung:{user_id}:thu_hoi", before, {"trang_thai": "thu_hoi", "ly_do": body.ly_do})
    return {"ok": True}


@router.post("/users/{user_id}/approve", tags=["nguoi-dung"])
async def approve(user_id: int, actor: CurrentUser = Depends(get_current_user)) -> dict:
    pw = temp_password()
    async with admin_sessionmaker()() as s:
        u = await _own_user(s, actor, user_id)
        if u.trang_thai != "cho_duyet":
            raise HTTPException(409, "Tài khoản không ở trạng thái chờ duyệt")
        roles = set((await s.execute(select(Grant.role).where(Grant.user_id == u.id))).scalars())
        if roles & NEED_LEADER_APPROVAL:
            if "lanh_dao" not in actor.roles or actor.id == u.nguoi_phe_duyet_id:
                raise HTTPException(403, "Tài khoản lãnh đạo, quản trị phải do lãnh đạo đơn vị phê duyệt")
        elif not actor.can("duyet", "quan_tri"):
            raise HTTPException(403, "Bạn không có quyền phê duyệt tài khoản")
        u.trang_thai = "hoat_dong"
        u.password_hash = hash_password(pw)
        u.phai_doi_mat_khau = True
        u.nguoi_phe_duyet_id = actor.id
        secret = None
        if roles & ROLES_2FA:
            u.totp_secret = secret = pyotp.random_base32()
        await s.commit()
    await record_change(actor, u.tenant_id, f"nguoi_dung:{user_id}:phe_duyet", {"trang_thai": "cho_duyet"}, {"trang_thai": "hoat_dong"})
    return {"ok": True, "mat_khau_tam": pw, "totp_secret": secret,
            "ghi_chu": "Mật khẩu tạm và mã xác thực 2 lớp chỉ hiển thị một lần; người dùng phải đổi mật khẩu khi đăng nhập"}


IMPORT_COLS = ["Tên đăng nhập", "Họ tên", "Đơn vị", "Chức danh", "Email", "Vai trò", "Nhóm dữ liệu", "Phạm vi khai thác", "Người phê duyệt"]


@router.post("/users/import", tags=["nguoi-dung"])
async def import_users(file: UploadFile = File(...), actor: CurrentUser = Depends(require("nhap", "quan_tri"))) -> dict:
    if actor.tenant_id is None:
        raise HTTPException(400, "Chỉ quản trị đơn vị được nhập danh sách tài khoản")
    raw = await file.read()
    try:
        ws = load_workbook(io.BytesIO(raw), read_only=True, data_only=True).active
    except Exception as e:  # noqa: BLE001
        raise HTTPException(422, "Tệp không phải Excel (.xlsx) hợp lệ") from e
    rows = list(ws.iter_rows(values_only=True))
    header = [str(c or "").strip() for c in rows[0]] if rows else []
    if header[: len(IMPORT_COLS)] != IMPORT_COLS:
        raise HTTPException(422, {"loi": [{"dong": 1, "cot": "", "thong_bao": "Sai mẫu: hãy tải biểu mẫu tài khoản mới nhất"}]})
    loi: list[dict] = []
    parsed: list[dict] = []
    async with admin_sessionmaker()() as s:
        for i, r in enumerate(rows[1:], start=2):
            v = {k: (str(c).strip() if c is not None else "") for k, c in zip(IMPORT_COLS, r)}
            if not any(v.values()):
                continue
            for k in ["Tên đăng nhập", "Họ tên", "Vai trò"]:
                if not v[k]:
                    loi.append({"dong": i, "cot": k, "thong_bao": f"Bắt buộc nhập {k.lower()}"})
            if not v["Người phê duyệt"]:
                loi.append({"dong": i, "cot": "Người phê duyệt", "thong_bao": "Bắt buộc ghi người phê duyệt"})
            if v["Vai trò"] and v["Vai trò"] not in ROLES:
                loi.append({"dong": i, "cot": "Vai trò", "thong_bao": f"Vai trò '{v['Vai trò']}' không có trong danh mục"})
            elif v["Vai trò"] and v["Vai trò"] not in UNIT_CREATABLE:
                loi.append({"dong": i, "cot": "Vai trò", "thong_bao": f"Vai trò '{v['Vai trò']}' không được tạo bởi quản trị đơn vị"})
            nhom = [x.strip() for x in v["Nhóm dữ liệu"].split(",") if x.strip()] or None
            try:
                if v["Vai trò"] in UNIT_CREATABLE:
                    default_grants(v["Vai trò"], nhom)
            except ValueError as e:
                loi.append({"dong": i, "cot": "Nhóm dữ liệu", "thong_bao": str(e)})
            if v["Tên đăng nhập"] and (await s.execute(select(User.id).where(User.username == v["Tên đăng nhập"]))).scalar():
                loi.append({"dong": i, "cot": "Tên đăng nhập", "thong_bao": "Tên đăng nhập đã tồn tại"})
            parsed.append({**v, "nhom": nhom})
        if loi:
            raise HTTPException(422, {"loi": loi})
        created = []
        for v in parsed:
            u = User(tenant_id=actor.tenant_id, username=v["Tên đăng nhập"], ho_ten=v["Họ tên"], don_vi=v["Đơn vị"],
                     chuc_danh=v["Chức danh"], email=v["Email"] or None, pham_vi_khai_thac=v["Phạm vi khai thác"],
                     trang_thai="cho_duyet")
            s.add(u)
            await s.flush()
            for g_nhom, g_quyen in default_grants(v["Vai trò"], v["nhom"]):
                s.add(Grant(user_id=u.id, tenant_id=actor.tenant_id, role=v["Vai trò"], nhom_du_lieu=g_nhom, quyen=g_quyen))
            created.append({"id": u.id, "username": u.username, "nguoi_phe_duyet": v["Người phê duyệt"]})
        await s.commit()
    await record_change(actor, actor.tenant_id, "nguoi_dung:import", None, {"tao_moi": [c["username"] for c in created]})
    return {"tao_moi": created}


class ChangePwIn(BaseModel):
    mat_khau_cu: str
    mat_khau_moi: str


def password_problem(pw: str) -> str | None:
    if len(pw) < 10:
        return "Mật khẩu mới phải có ít nhất 10 ký tự, gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt"
    checks = [any(c.isupper() for c in pw), any(c.islower() for c in pw), any(c.isdigit() for c in pw), any(not c.isalnum() for c in pw)]
    if not all(checks):
        return "Mật khẩu mới phải có ít nhất 10 ký tự, gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt"
    return None


@router.post("/auth/change-password")
async def change_password(body: ChangePwIn, user: CurrentUser = Depends(get_current_user)) -> dict:
    async with admin_sessionmaker()() as s:
        u = await s.get(User, user.id)
        if not verify_password(body.mat_khau_cu, u.password_hash):
            raise HTTPException(400, "Mật khẩu hiện tại không đúng")
        if (p := password_problem(body.mat_khau_moi)) is not None:
            raise HTTPException(422, p)
        if body.mat_khau_moi == body.mat_khau_cu:
            raise HTTPException(422, "Mật khẩu mới phải khác mật khẩu hiện tại")
        u.password_hash = hash_password(body.mat_khau_moi)
        u.phai_doi_mat_khau = False
        u.token_version += 1
        await s.commit()
    await record_change(user, user.tenant_id, f"nguoi_dung:{user.id}:doi_mat_khau", None, {"doi_mat_khau": True})
    return {"ok": True, "ghi_chu": "Đăng nhập lại bằng mật khẩu mới"}
