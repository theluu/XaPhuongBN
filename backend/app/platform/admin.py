"""Quản trị nền tảng (khởi tạo đơn vị) và quản trị đơn vị (người dùng, kế hoạch, quy tắc, nhật ký, dữ liệu minh họa, xuất dữ liệu)."""
import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pyotp
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models import AlertRule
from app.alerts.rules import RULES
from app.audit.models import AuditLog
from app.audit.service import record_change
from app.auth.deps import require, tenant_db
from app.auth.models import Grant, User
from app.auth.roles import ROLES, default_grants
from app.auth.security import hash_password, temp_password
from app.catalog.models import Indicator, IndicatorPlan, TemplatePack
from app.catalog.packs import apply_pack
from app.core.db import Base, admin_sessionmaker, import_models
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.platform.models import ResidentialGroup, Tenant
from app.sources.service import PHAN_HE

platform = APIRouter(prefix="/api/platform", tags=["quan-tri-nen-tang"])
admin = APIRouter(prefix="/api/admin", tags=["quan-tri-don-vi"])
PLATFORM = require("duyet", "he_thong")
UNIT_READ = require("doc", "quan_tri")
UNIT_WRITE = require("duyet", "quan_tri")


# ---------------- Nền tảng ----------------
@platform.get("/tenants")
async def tenants(_: CurrentUser = Depends(PLATFORM)) -> list:
    async with admin_sessionmaker()() as s:
        rows = (await s.execute(select(Tenant).order_by(Tenant.id))).scalars()
        out = []
        for t in rows:
            n_users = (await s.execute(text("SELECT count(*) FROM app_user WHERE tenant_id=:t"), {"t": t.id})).scalar()
            n_ind = (await s.execute(text("SELECT count(*) FROM indicator WHERE tenant_id=:t"), {"t": t.id})).scalar()
            out.append({"id": t.id, "ma_dvhc": t.ma_dvhc, "ten": t.ten, "cap": t.cap, "parent_id": t.parent_id, "trang_thai": t.trang_thai,
                        "so_nguoi_dung": n_users, "so_chi_tieu": n_ind})
        return out


@platform.get("/packs")
async def packs(_: CurrentUser = Depends(PLATFORM)) -> list:
    async with admin_sessionmaker()() as s:
        return [{"ma": p.ma, "ten": p.ten, "phien_ban": p.phien_ban, "so_chi_tieu": len(p.noi_dung.get("indicators", []))}
                for p in (await s.execute(select(TemplatePack).order_by(TemplatePack.ma))).scalars()]


class Leader(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    ho_ten: str = Field(min_length=1)
    chuc_danh: str = ""


class OnboardIn(BaseModel):
    ma_dvhc: str = Field(min_length=1, max_length=20)
    ten: str = Field(min_length=1)
    cap: str = Field(pattern="^(xa|phuong)$")
    parent_id: int | None = None
    pack: str
    so_tdp: int = Field(ge=0, le=200)
    lanh_dao: Leader
    quan_tri: Leader | None = None


async def _new_user(s: AsyncSession, tenant_id: int, u: Leader, role: str, nhom: list[str] | None = None, extra_roles: list[str] | None = None) -> tuple[User, str]:
    if (await s.execute(select(User.id).where(User.username == u.username))).scalar():
        raise HTTPException(409, f"Tên đăng nhập {u.username} đã tồn tại")
    pw = temp_password()
    row = User(tenant_id=tenant_id, username=u.username, ho_ten=u.ho_ten, chuc_danh=u.chuc_danh, trang_thai="hoat_dong",
               password_hash=hash_password(pw), phai_doi_mat_khau=True)
    s.add(row)
    await s.flush()
    for r in [role, *(extra_roles or [])]:
        for g_nhom, g_quyen in default_grants(r, nhom):
            s.add(Grant(user_id=row.id, tenant_id=tenant_id, role=r, nhom_du_lieu=g_nhom, quyen=g_quyen))
    return row, pw


@platform.post("/onboard", status_code=201)
async def onboard(body: OnboardIn, user: CurrentUser = Depends(PLATFORM)) -> dict:
    """Khởi tạo xã/phường mới: đơn vị → gói mẫu → tổ dân phố → tài khoản lãnh đạo (DT: nền tảng dùng chung)."""
    async with admin_sessionmaker()() as s:
        if (await s.execute(select(Tenant.id).where(Tenant.ma_dvhc == body.ma_dvhc))).scalar():
            raise HTTPException(409, "Mã đơn vị hành chính đã có trên nền tảng")
        pack = (await s.execute(select(TemplatePack).where(TemplatePack.ma == body.pack))).scalar()
        if pack is None:
            raise HTTPException(422, "Không có gói mẫu này")
        t = Tenant(ma_dvhc=body.ma_dvhc, ten=body.ten.strip(), cap=body.cap, parent_id=body.parent_id, config={"cho_phep_theo_tdp": False},
                   modules={p: "bat" for p in PHAN_HE})
        s.add(t)
        await s.flush()
        await apply_pack(s, t.id, pack.noi_dung)
        for i in range(1, body.so_tdp + 1):
            s.add(ResidentialGroup(tenant_id=t.id, ma_tdp=f"TDP{i:02d}", ten=f"Tổ dân phố số {i}"))
        leader, pw = await _new_user(s, t.id, body.lanh_dao, "lanh_dao", extra_roles=None if body.quan_tri else ["quan_tri_don_vi"])
        admin_pw = None
        if body.quan_tri:
            _, admin_pw = await _new_user(s, t.id, body.quan_tri, "quan_tri_don_vi")
        await s.commit()
        n_ind = (await s.execute(text("SELECT count(*) FROM indicator WHERE tenant_id=:t"), {"t": t.id})).scalar()
    await record_change(user, t.id, f"don_vi:{t.id}:khoi_tao", None, {"ma_dvhc": body.ma_dvhc, "ten": body.ten, "pack": body.pack})
    return {"tenant_id": t.id, "so_chi_tieu": n_ind, "so_tdp": body.so_tdp, "lanh_dao": body.lanh_dao.username, "mat_khau_tam": pw,
            "mat_khau_tam_quan_tri": admin_pw, "ghi_chu": "Mật khẩu tạm chỉ hiển thị một lần; người dùng phải đổi khi đăng nhập lần đầu"}


# ---------------- Đơn vị ----------------
def _user_out(u: User, grants: list[Grant]) -> dict:
    return {"id": u.id, "username": u.username, "ho_ten": u.ho_ten, "chuc_danh": u.chuc_danh, "don_vi": u.don_vi, "trang_thai": u.trang_thai,
            "roles": sorted({g.role for g in grants}), "nhom": sorted({n for g in grants for n in (g.nhom_du_lieu or ["*"])}),
            "co_2fa": bool(u.totp_secret), "phai_doi_mat_khau": u.phai_doi_mat_khau}


@admin.get("/users")
async def users(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(UNIT_READ)) -> list:
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as a:
        us = list((await a.execute(select(User).where(User.tenant_id == tid).order_by(User.ho_ten))).scalars())
        gs = list((await a.execute(select(Grant).where(Grant.user_id.in_([u.id for u in us])))).scalars()) if us else []
    return [_user_out(u, [g for g in gs if g.user_id == u.id]) for u in us]


class UserIn(Leader):
    don_vi: str = ""
    role: str
    nhom: list[str] | None = None


@admin.post("/users", status_code=201)
async def create_user(body: UserIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    if body.role not in ROLES or body.role == "quan_tri_nen_tang":
        raise HTTPException(422, "Vai trò không hợp lệ")
    try:
        default_grants(body.role, body.nhom)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as a:
        u, pw = await _new_user(a, tid, body, body.role, body.nhom)
        u.don_vi, u.nguoi_phe_duyet_id = body.don_vi, user.id
        await a.commit()
    await record_change(user, tid, f"nguoi_dung:{u.id}:tao", None, {"username": u.username, "role": body.role, "nhom": body.nhom})
    return {"id": u.id, "username": u.username, "mat_khau_tam": pw}


@admin.post("/users/{uid}/totp")
async def setup_totp(uid: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as a:
        u = await a.get(User, uid)
        if u is None or u.tenant_id != tid:
            raise HTTPException(404, "Không tìm thấy người dùng")
        u.totp_secret = pyotp.random_base32()
        u.token_version += 1
        await a.commit()
        secret, name = u.totp_secret, u.username
    await record_change(user, tid, f"nguoi_dung:{uid}:cap_2fa", None, {"cap_ma_2fa": True})
    return {"secret": secret, "otpauth_uri": pyotp.TOTP(secret).provisioning_uri(name=name, issuer_name="IOC-XP"),
            "ghi_chu": "Quét mã bằng ứng dụng xác thực (Google Authenticator, Microsoft Authenticator). Mã chỉ hiển thị một lần."}


class PlanIn(BaseModel):
    ky: str
    gia_tri: float
    can_cu: str = ""


async def _ind(s: AsyncSession, ma: str) -> Indicator:
    i = (await s.execute(select(Indicator).where(Indicator.tenant_id == s.info["tenant_id"], Indicator.ma_chi_tieu == ma))).scalar()
    if i is None:
        raise HTTPException(404, "Không tìm thấy chỉ tiêu")
    return i


@admin.get("/indicators/{ma}/plans")
async def plans(ma: str, s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(UNIT_READ)) -> list:
    i = await _ind(s, ma)
    rows = (await s.execute(select(IndicatorPlan).where(IndicatorPlan.indicator_id == i.id).order_by(IndicatorPlan.ky))).scalars()
    return jsonable([{"ky": p.ky, "gia_tri": p.gia_tri_ke_hoach, "can_cu": p.can_cu} for p in rows])


@admin.put("/indicators/{ma}/plans")
async def put_plan(ma: str, body: PlanIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(require("nhap", "quan_tri"))) -> dict:
    from app.core.periods import parse_ky

    i = await _ind(s, ma)
    ky = str(parse_ky(body.ky))
    p = (await s.execute(select(IndicatorPlan).where(IndicatorPlan.indicator_id == i.id, IndicatorPlan.ky == ky))).scalar()
    before = None if p is None else {"gia_tri": float(p.gia_tri_ke_hoach), "can_cu": p.can_cu}
    if p is None:
        p = IndicatorPlan(indicator_id=i.id, tenant_id=i.tenant_id, nam=int(ky[:4]), ky=ky, gia_tri_ke_hoach=Decimal(str(body.gia_tri)))
        s.add(p)
    p.gia_tri_ke_hoach, p.can_cu = Decimal(str(body.gia_tri)), body.can_cu
    await s.commit()
    await record_change(user, i.tenant_id, f"ke_hoach:{ma}:{ky}", before, {"gia_tri": body.gia_tri, "can_cu": body.can_cu})
    return {"ok": True}


@admin.get("/alert-rules")
async def rules(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(UNIT_READ)) -> list:
    cfg = {r.ma: r for r in (await s.execute(select(AlertRule).where(AlertRule.tenant_id == s.info["tenant_id"]))).scalars()}
    return [{"ma": r.ma, "ten": r.ten, "loai": r.loai, "can_cu": r.dt, "bat": cfg[r.ma].bat if r.ma in cfg else True} for r in RULES.values()]


class RuleIn(BaseModel):
    bat: bool


@admin.put("/alert-rules/{ma}")
async def put_rule(ma: str, body: RuleIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    if ma not in RULES:
        raise HTTPException(404, "Không có quy tắc này")
    tid = s.info["tenant_id"]
    r = (await s.execute(select(AlertRule).where(AlertRule.tenant_id == tid, AlertRule.ma == ma))).scalar()
    if r is None:
        r = AlertRule(tenant_id=tid, ma=ma, params={})
        s.add(r)
    r.bat = body.bat
    await s.commit()
    await record_change(user, tid, f"quy_tac:{ma}", None, {"bat": body.bat})
    return {"ok": True}


@admin.get("/audit")
async def audit(limit: int = 200, user_id: int | None = None, s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(UNIT_READ)) -> list:
    q = select(AuditLog).where(AuditLog.tenant_id == s.info["tenant_id"])
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    async with admin_sessionmaker()() as a:
        rows = (await a.execute(q.order_by(AuditLog.id.desc()).limit(min(limit, 1000)))).scalars()
        return jsonable([{"id": r.id, "ts": r.ts, "user_id": r.user_id, "tenant_id": r.tenant_id, "ip": r.ip, "method": r.method, "path": r.path,
                          "status": r.status, "doi_tuong": r.doi_tuong, "before": r.before, "after": r.after} for r in rows])


class PurgeIn(BaseModel):
    xac_nhan: str


@admin.post("/purge-sample")
async def purge(body: PurgeIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    """Xóa toàn bộ dữ liệu minh họa trước khi dùng thật (DT V.3: không dùng số giả lập làm kết quả thực tế)."""
    if body.xac_nhan != "XÓA DỮ LIỆU MINH HỌA":
        raise HTTPException(422, "Gõ chính xác cụm 'XÓA DỮ LIỆU MINH HỌA' để xác nhận")
    from seeds.run import purge_sample_by_id

    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as a:
        n = await purge_sample_by_id(a, tid)
        await a.commit()
    await record_change(user, tid, f"don_vi:{tid}:xoa_minh_hoa", None, {"da_xoa": n})
    return {"da_xoa": n}


class TenantIn(BaseModel):
    ten_co_quan: list[str] | None = None
    logo_key: str | None = None
    cho_phep_theo_tdp: bool | None = None
    tile_url: str | None = None


@admin.patch("/tenant")
async def patch_tenant(body: TenantIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    tid = s.info["tenant_id"]
    if body.logo_key:
        from app.files.models import StoredFile
        from app.files.storage import IMAGE_TYPES

        f = (await s.execute(select(StoredFile).where(StoredFile.key == body.logo_key))).scalar()
        if f is None or f.content_type not in IMAGE_TYPES:
            raise HTTPException(422, "Biểu trưng phải là tệp ảnh đã tải lên")
    async with admin_sessionmaker()() as a:
        t = await a.get(Tenant, tid)
        cfg = dict(t.config or {})
        if body.ten_co_quan is not None:
            cfg["ten_co_quan"] = [x.strip() for x in body.ten_co_quan if x.strip()][:2]
        if body.cho_phep_theo_tdp is not None:
            cfg["cho_phep_theo_tdp"] = body.cho_phep_theo_tdp
        if body.tile_url is not None:
            cfg["ban_do"] = {**(cfg.get("ban_do") or {}), "tile_url": body.tile_url}
        t.config = cfg
        if body.logo_key:
            t.logo_key = body.logo_key
        await a.commit()
    await record_change(user, tid, f"don_vi:{tid}:cau_hinh", None, body.model_dump(exclude_none=True))
    return {"ok": True}


SECRET_COLS = {"password_hash", "totp_secret"}


@admin.get("/export")
async def export(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> Response:
    """Xuất toàn bộ dữ liệu của đơn vị (không khóa đơn vị vào nền tảng). Không gồm mật khẩu, khóa 2FA, nhật ký."""
    import_models()
    tid = s.info["tenant_id"]
    out: dict = {"don_vi_id": tid, "xuat_luc": datetime.now(UTC).isoformat()}
    for table in Base.metadata.sorted_tables:
        if "tenant_id" not in table.c or table.name == "audit_log" or not table.info.get("rls"):
            continue
        rows = (await s.execute(select(table).where(table.c.tenant_id == tid))).mappings().all()
        out[table.name] = [{k: v for k, v in r.items() if k not in SECRET_COLS} for r in rows]
    await record_change(user, tid, f"don_vi:{tid}:xuat_du_lieu", None, {"so_bang": len(out) - 2})
    body = json.dumps(jsonable(out), ensure_ascii=False, default=str)
    return Response(body, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="du-lieu-don-vi-{tid}-{date.today().isoformat()}.json"'})
