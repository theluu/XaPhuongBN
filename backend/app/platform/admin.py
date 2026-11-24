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
from app.auth.roles import NEED_LEADER_APPROVAL, ROLES_2FA, UNIT_CREATABLE, default_grants  # noqa: F401
from app.auth.security import hash_password, temp_password
from app.catalog.models import Indicator, IndicatorPlan, TemplatePack
from app.catalog.packs import apply_pack
from app.core.db import Base, admin_sessionmaker, import_models
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.platform.models import ResidentialGroup, Tenant
from app.platform.structure import dia_ban_label
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
    tam: list[float] | None = Field(None, min_length=2, max_length=2)  # tâm bản đồ [vĩ độ, kinh độ]


async def _new_user(s: AsyncSession, tenant_id: int, u: Leader, role: str, nhom: list[str] | None = None, extra_roles: list[str] | None = None,
                    pending: bool = False) -> tuple[User, str | None, str | None]:
    if (await s.execute(select(User.id).where(User.username == u.username))).scalar():
        raise HTTPException(409, f"Tên đăng nhập {u.username} đã tồn tại")
    pw = None if pending else temp_password()
    secret = None if pending or not ({role, *(extra_roles or [])} & ROLES_2FA) else pyotp.random_base32()
    row = User(tenant_id=tenant_id, username=u.username, ho_ten=u.ho_ten, chuc_danh=u.chuc_danh, trang_thai="cho_duyet" if pending else "hoat_dong",
               password_hash=hash_password(pw) if pw else None, phai_doi_mat_khau=True, totp_secret=secret)
    s.add(row)
    await s.flush()
    for r in [role, *(extra_roles or [])]:
        for g_nhom, g_quyen in default_grants(r, nhom):
            s.add(Grant(user_id=row.id, tenant_id=tenant_id, role=r, nhom_du_lieu=g_nhom, quyen=g_quyen))
    return row, pw, secret


@platform.post("/onboard", status_code=201)
async def onboard(body: OnboardIn, user: CurrentUser = Depends(PLATFORM)) -> dict:
    """Khởi tạo xã/phường mới: đơn vị → gói mẫu → tổ dân phố → tài khoản lãnh đạo (DT: nền tảng dùng chung)."""
    async with admin_sessionmaker()() as s:
        if (await s.execute(select(Tenant.id).where(Tenant.ma_dvhc == body.ma_dvhc))).scalar():
            raise HTTPException(409, "Mã đơn vị hành chính đã có trên nền tảng")
        pack = (await s.execute(select(TemplatePack).where(TemplatePack.ma == body.pack))).scalar()
        if pack is None:
            raise HTTPException(422, "Không có gói mẫu này")
        cfg: dict = {"cho_phep_theo_tdp": False}
        if body.tam:
            lat, lng = body.tam
            if not (8 <= lat <= 24 and 102 <= lng <= 110):
                raise HTTPException(422, "Tọa độ tâm bản đồ phải nằm trong lãnh thổ Việt Nam")
            cfg["ban_do"] = {"tam": [lat, lng], "zoom": 14, "bbox": [round(lat - 0.025, 4), round(lng - 0.035, 4), round(lat + 0.025, 4), round(lng + 0.035, 4)]}
        t = Tenant(ma_dvhc=body.ma_dvhc, ten=body.ten.strip(), cap=body.cap, parent_id=body.parent_id, config=cfg,
                   modules={p: "bat" for p in PHAN_HE})
        s.add(t)
        await s.flush()
        await apply_pack(s, t.id, pack.noi_dung)
        from app.dau_moi.service import ensure as ensure_dau_moi

        await ensure_dau_moi(s, t.id, t.ten)
        nhan, ma = dia_ban_label(body.cap), "TDP" if body.cap == "phuong" else "THON"
        for i in range(1, body.so_tdp + 1):
            s.add(ResidentialGroup(tenant_id=t.id, ma_tdp=f"{ma}{i:02d}", ten=f"{nhan} số {i}", loai="tdp" if body.cap == "phuong" else "thon"))
        leader, pw, secret = await _new_user(s, t.id, body.lanh_dao, "lanh_dao", extra_roles=None if body.quan_tri else ["quan_tri_don_vi"])
        admin_pw = admin_secret = None
        if body.quan_tri:
            _, admin_pw, admin_secret = await _new_user(s, t.id, body.quan_tri, "quan_tri_don_vi")
        await s.commit()
        n_ind = (await s.execute(text("SELECT count(*) FROM indicator WHERE tenant_id=:t"), {"t": t.id})).scalar()
    await record_change(user, t.id, f"don_vi:{t.id}:khoi_tao", None, {"ma_dvhc": body.ma_dvhc, "ten": body.ten, "pack": body.pack})
    return {"tenant_id": t.id, "so_chi_tieu": n_ind, "so_tdp": body.so_tdp, "lanh_dao": body.lanh_dao.username, "mat_khau_tam": pw,
            "totp_secret": secret, "mat_khau_tam_quan_tri": admin_pw, "totp_secret_quan_tri": admin_secret, "ghi_chu": "Mật khẩu tạm chỉ hiển thị một lần; người dùng phải đổi khi đăng nhập lần đầu"}


# ---------------- Đơn vị ----------------
def _user_out(u: User, grants: list[Grant]) -> dict:
    return {"id": u.id, "username": u.username, "ho_ten": u.ho_ten, "chuc_danh": u.chuc_danh, "don_vi": u.don_vi, "trang_thai": u.trang_thai,
            "roles": sorted({g.role for g in grants}), "nhom": sorted({n for g in grants for n in (g.nhom_du_lieu or ["*"])}),
            "co_2fa": bool(u.totp_secret), "phai_doi_mat_khau": u.phai_doi_mat_khau, "email": u.email, "ly_do_thu_hoi": u.ly_do_thu_hoi,
            "bi_khoa": bool(u.locked_until and u.locked_until > datetime.now(UTC))}


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
    if body.role not in UNIT_CREATABLE:
        raise HTTPException(422, "Vai trò không hợp lệ hoặc không được tạo bởi quản trị đơn vị")
    try:
        default_grants(body.role, body.nhom)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as a:
        pending = body.role in NEED_LEADER_APPROVAL
        u, pw, secret = await _new_user(a, tid, body, body.role, body.nhom, pending=pending)
        u.don_vi = body.don_vi
        u.nguoi_phe_duyet_id = user.id  # người tạo; khi phê duyệt sẽ ghi người phê duyệt (không được là người tạo)
        await a.commit()
    await record_change(user, tid, f"nguoi_dung:{u.id}:tao", None, {"username": u.username, "role": body.role, "nhom": body.nhom})
    return {"id": u.id, "username": u.username, "trang_thai": u.trang_thai, "mat_khau_tam": pw, "totp_secret": secret,
            "ghi_chu": "Tài khoản lãnh đạo/quản trị chờ lãnh đạo đơn vị phê duyệt" if pending else "Mật khẩu và mã 2 lớp chỉ hiển thị một lần"}


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
    lien_ket: list[dict] | None = None  # [{ten, url}] liên kết nhanh trên dải bản tin
    nguon_tin: list[dict] | None = None  # [{ten, url}] nguồn RSS/Atom (Cổng TTĐT…)


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
        if body.lien_ket is not None:
            links = []
            for x in body.lien_ket[:12]:
                ten, url = str(x.get("ten", "")).strip(), str(x.get("url", "")).strip()
                if not ten or not (url.startswith("https://") or url.startswith("/")) or len(url) > 500:
                    raise HTTPException(422, "Liên kết cần có tên và địa chỉ https:// (hoặc đường dẫn trong hệ thống bắt đầu bằng /)")
                links.append({"ten": ten[:80], "url": url})
            cfg["lien_ket"] = links
        if body.nguon_tin is not None:
            from app.tin_ngoai.service import FeedError, check_url

            srcs = []
            for x in body.nguon_tin[:5]:
                ten = str(x.get("ten", "")).strip()
                try:
                    url = check_url(str(x.get("url", "")))
                except FeedError as e:
                    raise HTTPException(422, str(e)) from e
                if not ten:
                    raise HTTPException(422, "Nguồn tin cần có tên")
                srcs.append({"ten": ten[:80], "url": url})
            cfg["nguon_tin"] = srcs
        t.config = cfg
        if body.logo_key:
            t.logo_key = body.logo_key
        await a.commit()
    await record_change(user, tid, f"don_vi:{tid}:cau_hinh", None, body.model_dump(exclude_none=True))
    return {"ok": True}


@admin.get("/nguon-tin")
async def feeds(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(UNIT_READ)) -> dict:
    t = await s.get(Tenant, s.info["tenant_id"])
    cfg = t.config or {}
    return {"nguon_tin": cfg.get("nguon_tin") or [], "trang_thai": cfg.get("nguon_tin_trang_thai") or {}}


@admin.post("/nguon-tin/lam-moi")
async def refresh_feeds(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    """Lấy tin ngay từ các nguồn RSS/Atom của đơn vị."""
    from app.tin_ngoai.service import refresh_tenant

    tid = s.info["tenant_id"]
    st = await refresh_tenant(tid)
    await record_change(user, tid, f"don_vi:{tid}:lay_nguon_tin", None, {k: {"ok": v["ok"], "so_tin": v["so_tin"]} for k, v in st.items()})
    return {"trang_thai": st}


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


# ---------------- Người dùng: sửa quyền, đặt lại mật khẩu, mở khóa, khôi phục ----------------
async def _unit_user(a: AsyncSession, tid: int, uid: int) -> User:
    u = await a.get(User, uid)
    if u is None or u.tenant_id != tid:
        raise HTTPException(404, "Không tìm thấy người dùng")
    return u


class UserPatch(BaseModel):
    ho_ten: str | None = None
    chuc_danh: str | None = None
    don_vi: str | None = None
    email: str | None = None
    role: str | None = None
    nhom: list[str] | None = None


@admin.patch("/users/{uid}")
async def patch_user(uid: int, body: UserPatch, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as a:
        u = await _unit_user(a, tid, uid)
        gs = list((await a.execute(select(Grant).where(Grant.user_id == uid))).scalars())
        before = _user_out(u, gs)
        for k in ("ho_ten", "chuc_danh", "don_vi", "email"):
            v = getattr(body, k)
            if v is not None:
                if k == "ho_ten" and not v.strip():
                    raise HTTPException(422, "Họ tên không được để trống")
                setattr(u, k, v.strip() or (None if k == "email" else ""))
        if body.role is not None:
            if body.role not in UNIT_CREATABLE:
                raise HTTPException(422, "Vai trò không hợp lệ")
            if body.role in NEED_LEADER_APPROVAL and "lanh_dao" not in user.roles:
                raise HTTPException(403, "Cấp vai trò lãnh đạo hoặc quản trị đơn vị cần lãnh đạo đơn vị thực hiện")
            if uid == user.id and body.role != "quan_tri_don_vi" and "quan_tri_don_vi" in before["roles"]:
                raise HTTPException(409, "Không tự gỡ quyền quản trị của chính mình; nhờ quản trị viên khác thực hiện")
            try:
                grants = default_grants(body.role, body.nhom)
            except ValueError as e:
                raise HTTPException(422, str(e)) from e
            for g in gs:
                await a.delete(g)
            for g_nhom, g_quyen in grants:
                a.add(Grant(user_id=uid, tenant_id=tid, role=body.role, nhom_du_lieu=g_nhom, quyen=g_quyen))
            u.token_version += 1  # quyền mới có hiệu lực ngay, buộc đăng nhập lại
        await a.commit()
        gs = list((await a.execute(select(Grant).where(Grant.user_id == uid))).scalars())
        after = _user_out(u, gs)
    await record_change(user, tid, f"nguoi_dung:{uid}:sua", before, after)
    return after


@admin.post("/users/{uid}/reset-password")
async def reset_password(uid: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    tid = s.info["tenant_id"]
    pw = temp_password()
    async with admin_sessionmaker()() as a:
        u = await _unit_user(a, tid, uid)
        if u.trang_thai != "hoat_dong":
            raise HTTPException(409, "Chỉ đặt lại mật khẩu cho tài khoản đang hoạt động")
        u.password_hash, u.phai_doi_mat_khau = hash_password(pw), True
        u.failed_count, u.locked_until = 0, None
        u.token_version += 1
        await a.commit()
        name = u.username
    await record_change(user, tid, f"nguoi_dung:{uid}:dat_lai_mat_khau", None, {"dat_lai": True})
    return {"username": name, "mat_khau_tam": pw, "ghi_chu": "Mật khẩu tạm chỉ hiển thị một lần; người dùng phải đổi khi đăng nhập"}


@admin.post("/users/{uid}/unlock")
async def unlock(uid: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as a:
        u = await _unit_user(a, tid, uid)
        u.failed_count, u.locked_until = 0, None
        await a.commit()
    await record_change(user, tid, f"nguoi_dung:{uid}:mo_khoa", None, {"mo_khoa": True})
    return {"ok": True}


@admin.post("/users/{uid}/restore")
async def restore(uid: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    """Khôi phục tài khoản đã thu hồi: cấp mật khẩu tạm mới, buộc đổi khi đăng nhập."""
    tid = s.info["tenant_id"]
    pw = temp_password()
    async with admin_sessionmaker()() as a:
        u = await _unit_user(a, tid, uid)
        if u.trang_thai != "thu_hoi":
            raise HTTPException(409, "Tài khoản không ở trạng thái đã thu hồi")
        u.trang_thai, u.ly_do_thu_hoi = "hoat_dong", None
        u.password_hash, u.phai_doi_mat_khau = hash_password(pw), True
        u.token_version += 1
        await a.commit()
        name = u.username
    await record_change(user, tid, f"nguoi_dung:{uid}:khoi_phuc", {"trang_thai": "thu_hoi"}, {"trang_thai": "hoat_dong"})
    return {"username": name, "mat_khau_tam": pw}


@admin.get("/roles")
async def role_matrix(_: CurrentUser = Depends(UNIT_READ)) -> dict:
    """Ma trận phân quyền mặc định: vai trò × nhóm dữ liệu → đọc/nhập/duyệt."""
    from app.auth.roles import NHOM_DU_LIEU, NHOM_NGHIEP_VU, ROLES, ROLES_2FA

    out = []
    for ma, ten in ROLES.items():
        if ma == "quan_tri_nen_tang":
            continue
        sample = NHOM_NGHIEP_VU if ma in ("xac_nhan", "nhap_lieu", "chuyen_nganh") else None
        cells: dict[str, list[str]] = {}
        for g_nhom, g_quyen in default_grants(ma, sample):
            for n in g_nhom or NHOM_DU_LIEU:
                cells.setdefault(n, [])
                cells[n] = sorted(set(cells[n]) | set(g_quyen))
        out.append({"ma": ma, "ten": ten, "can_2fa": ma in ROLES_2FA, "theo_nhom_giao": sample is not None,
                    "quyen": {n: cells.get(n, []) for n in NHOM_DU_LIEU if n != "he_thong"}})
    return {"nhom": [n for n in NHOM_DU_LIEU if n != "he_thong"], "vai_tro": out}


# ---------------- Danh mục: thôn/tổ dân phố, phòng ban, lĩnh vực phản ánh ----------------
class GroupIn(BaseModel):
    ma_tdp: str = Field(min_length=1, max_length=30)
    ten: str = Field(min_length=1, max_length=200)
    loai: str | None = Field(None, pattern="^(thon|tdp)$")
    nguoi_dung_dau: str | None = None
    dien_thoai: str | None = Field(None, max_length=30)
    lat: float | None = None
    lng: float | None = None
    ngung_hoat_dong: bool | None = None


def _group_out(g: ResidentialGroup) -> dict:
    return jsonable({"id": g.id, "ma": g.ma_tdp, "ten": g.ten, "loai": g.loai, "nguoi_dung_dau": g.nguoi_dung_dau, "dien_thoai": g.dien_thoai,
                     "lat": g.lat, "lng": g.lng, "ngung_hoat_dong": bool(g.ngung_hoat_dong)})


def _group_apply(g: ResidentialGroup, body: GroupIn) -> None:
    if (body.lat is None) != (body.lng is None) or (body.lat is not None and not (8 <= body.lat <= 24 and 102 <= body.lng <= 110)):
        raise HTTPException(422, "Tọa độ không hợp lệ")
    g.ma_tdp, g.ten, g.loai = body.ma_tdp.strip(), body.ten.strip(), body.loai
    g.nguoi_dung_dau, g.dien_thoai = (body.nguoi_dung_dau or "").strip() or None, (body.dien_thoai or "").strip() or None
    g.lat = Decimal(str(body.lat)) if body.lat is not None else None
    g.lng = Decimal(str(body.lng)) if body.lng is not None else None
    g.ngung_hoat_dong = body.ngung_hoat_dong


@admin.get("/dia-ban")
async def groups(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(UNIT_READ)) -> list:
    rows = (await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == s.info["tenant_id"]).order_by(ResidentialGroup.ma_tdp))).scalars()
    return [_group_out(g) for g in rows]


@admin.post("/dia-ban", status_code=201)
async def add_group(body: GroupIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    tid = s.info["tenant_id"]
    if (await s.execute(select(ResidentialGroup.id).where(ResidentialGroup.tenant_id == tid, ResidentialGroup.ma_tdp == body.ma_tdp.strip()))).scalar():
        raise HTTPException(409, "Mã thôn/tổ dân phố đã tồn tại")
    g = ResidentialGroup(tenant_id=tid)
    _group_apply(g, body)
    s.add(g)
    await s.commit()
    await record_change(user, tid, f"dia_ban:{g.id}:tao", None, body.model_dump())
    return _group_out(g)


@admin.put("/dia-ban/{gid}")
async def put_group(gid: int, body: GroupIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    tid = s.info["tenant_id"]
    g = await s.get(ResidentialGroup, gid)
    if g is None or g.tenant_id != tid:
        raise HTTPException(404, "Không tìm thấy thôn/tổ dân phố")
    dup = (await s.execute(select(ResidentialGroup.id).where(ResidentialGroup.tenant_id == tid, ResidentialGroup.ma_tdp == body.ma_tdp.strip(),
                                                               ResidentialGroup.id != gid))).scalar()
    if dup:
        raise HTTPException(409, "Mã thôn/tổ dân phố đã tồn tại")
    before = _group_out(g)
    _group_apply(g, body)
    await s.commit()
    await record_change(user, tid, f"dia_ban:{gid}:sua", before, _group_out(g))
    return _group_out(g)


class CatalogIn(BaseModel):
    items: list[dict]


CATALOG_KEYS = {"phong-ban": ("phong_ban", {"ma", "ten"}), "linh-vuc": ("linh_vuc_phan_anh", {"ma", "ten", "chu_tri"})}


@admin.put("/danh-muc/{loai}")
async def put_catalog(loai: str, body: CatalogIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(UNIT_WRITE)) -> dict:
    """Sửa danh mục phòng ban (đơn vị phụ trách) hoặc lĩnh vực phản ánh của đơn vị."""
    from app.platform.structure import linh_vuc as lv_of, phong_ban as pb_of

    if loai not in CATALOG_KEYS:
        raise HTTPException(404, "Không có danh mục này")
    key, required = CATALOG_KEYS[loai]
    tid = s.info["tenant_id"]
    clean, seen = [], set()
    for i, it in enumerate(body.items, start=1):
        it = {k: (str(v).strip() if isinstance(v, str) else v) for k, v in it.items()}
        missing = [k for k in required if not it.get(k)]
        if missing:
            raise HTTPException(422, f"Dòng {i}: thiếu {', '.join(sorted(missing))}")
        if it["ma"] in seen:
            raise HTTPException(422, f"Dòng {i}: mã {it['ma']} bị trùng")
        seen.add(it["ma"])
        clean.append(it)
    if not clean:
        raise HTTPException(422, "Danh mục cần ít nhất một dòng")
    async with admin_sessionmaker()() as a:
        t = await a.get(Tenant, tid)
        cfg = dict(t.config or {})
        if loai == "linh-vuc":
            pb = {p["ma"] for p in pb_of(cfg, t.cap)}
            bad = [it["ma"] for it in clean if it["chu_tri"] not in pb]
            if bad:
                raise HTTPException(422, f"Đơn vị chủ trì không có trong danh mục phòng ban: {', '.join(bad)}")
            for it in clean:
                it["han_ngay"] = int(it.get("han_ngay") or 7)
        else:
            used = {lv["chu_tri"] for lv in lv_of(cfg, t.cap)}
            gone = used - seen
            if gone:
                raise HTTPException(422, f"Phòng ban đang chủ trì lĩnh vực phản ánh, chưa xóa được: {', '.join(sorted(gone))}")
        before = cfg.get(key)
        cfg[key] = clean
        t.config = cfg
        await a.commit()
    await record_change(user, tid, f"danh_muc:{key}", {"items": before}, {"items": clean})
    return {"items": clean}
