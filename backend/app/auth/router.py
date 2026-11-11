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
from app.auth.roles import ROLES, ROLES_2FA, default_grants
from app.auth.security import hash_password, make_token, temp_password, verify_password
from app.core.config import get_settings
from app.core.db import admin_sessionmaker
from app.core.principal import CurrentUser

router = APIRouter(prefix="/api", tags=["xac-thuc"])
BAD_LOGIN = "Sai tên đăng nhập hoặc mật khẩu"


class LoginIn(BaseModel):
    username: str
    password: str
    otp: str | None = None


def user_out(u: User, p: CurrentUser | None = None) -> dict:
    return {
        "id": u.id, "username": u.username, "ho_ten": u.ho_ten, "don_vi": u.don_vi, "chuc_danh": u.chuc_danh,
        "tenant_id": u.tenant_id, "phai_doi_mat_khau": u.phai_doi_mat_khau,
        "roles": sorted(p.roles) if p else [],
        "quyen": {k: sorted(v) for k, v in p.permissions.items()} if p else {},
    }


@router.post("/auth/login")
async def login(body: LoginIn, request: Request) -> dict:
    s_ = get_settings()
    now = datetime.now(UTC)
    status, detail, user_id, tenant_id = 401, BAD_LOGIN, None, None
    try:
        async with admin_sessionmaker()() as s:
            u = (await s.execute(select(User).where(User.username == body.username))).scalar()
            if u is None:
                verify_password(body.password, None)
                raise HTTPException(401, BAD_LOGIN)
            user_id, tenant_id = u.id, u.tenant_id
            if u.locked_until and u.locked_until > now:
                status = 423
                raise HTTPException(423, f"Tài khoản tạm khóa {s_.LOCKOUT_MINUTES} phút")
            if u.trang_thai != "hoat_dong" or not verify_password(body.password, u.password_hash):
                u.failed_count += 1
                if u.failed_count >= s_.LOCKOUT_THRESHOLD:
                    u.locked_until = now + timedelta(minutes=s_.LOCKOUT_MINUTES)
                    u.failed_count = 0
                await s.commit()
                raise HTTPException(401, BAD_LOGIN)
            roles = set((await s.execute(select(Grant.role).where(Grant.user_id == u.id))).scalars())
            if s_.REQUIRE_2FA and roles & ROLES_2FA:
                if not u.totp_secret:
                    raise HTTPException(403, "Tài khoản chưa thiết lập xác thực 2 lớp, liên hệ quản trị đơn vị")
                if not body.otp:
                    raise HTTPException(401, "Cần mã xác thực 2 lớp")
                if not pyotp.TOTP(u.totp_secret).verify(body.otp, valid_window=1):
                    raise HTTPException(401, "Mã xác thực không đúng")
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
async def approve(user_id: int, actor: CurrentUser = Depends(require("duyet", "quan_tri"))) -> dict:
    pw = temp_password()
    async with admin_sessionmaker()() as s:
        u = await _own_user(s, actor, user_id)
        if u.trang_thai != "cho_duyet":
            raise HTTPException(409, "Tài khoản không ở trạng thái chờ duyệt")
        u.trang_thai = "hoat_dong"
        u.password_hash = hash_password(pw)
        u.phai_doi_mat_khau = True
        u.nguoi_phe_duyet_id = actor.id
        await s.commit()
    await record_change(actor, u.tenant_id, f"nguoi_dung:{user_id}:phe_duyet", {"trang_thai": "cho_duyet"}, {"trang_thai": "hoat_dong"})
    return {"ok": True, "mat_khau_tam": pw, "ghi_chu": "Mật khẩu tạm chỉ hiển thị một lần; người dùng phải đổi khi đăng nhập"}


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
            nhom = [x.strip() for x in v["Nhóm dữ liệu"].split(",") if x.strip()] or None
            try:
                if v["Vai trò"] in ROLES:
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
