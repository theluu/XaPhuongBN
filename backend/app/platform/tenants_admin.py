"""Quản trị nền tảng: quản lý các xã/phường dùng chung hệ thống — sửa thông tin, tạm dừng/kích hoạt, xóa đơn vị,
quản lý tài khoản của từng đơn vị, nạp/xóa dữ liệu minh họa.

Nguyên tắc tách nhiệm: quản trị nền tảng quản lý *đơn vị và tài khoản*, chỉ xem số lượng bản ghi, không đọc nội dung
dữ liệu nghiệp vụ của phường (số liệu, phản ánh, người gửi…). Việc xem/sửa dữ liệu nghiệp vụ do quản trị đơn vị và cán bộ
của chính phường thực hiện."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from app.audit.service import record_change
from app.auth.models import Grant, User
from app.auth.roles import UNIT_CREATABLE, default_grants
from app.auth.security import hash_password, temp_password
from app.core.db import Base, admin_sessionmaker, import_models
from app.core.principal import CurrentUser
from app.platform.admin import PLATFORM, Leader, _new_user, _user_out
from app.platform.models import Tenant
from app.sources.service import PHAN_HE

router = APIRouter(prefix="/api/platform/tenants", tags=["quan-tri-nen-tang"])
UNIT_CAP = ("xa", "phuong")


async def _unit(a, tid: int) -> Tenant:  # noqa: ANN001
    t = await a.get(Tenant, tid)
    if t is None or t.cap not in UNIT_CAP:
        raise HTTPException(404, "Không tìm thấy xã/phường")
    return t


async def _counts(a, tid: int) -> dict:  # noqa: ANN001
    """Số bản ghi theo bảng (không đọc nội dung)."""
    import_models()
    tong = mau = 0
    for table in Base.metadata.sorted_tables:
        if "tenant_id" not in table.c or table.name in ("audit_log", "app_user", "user_grant") or not table.info.get("rls"):
            continue
        tong += (await a.execute(text(f'SELECT count(*) FROM "{table.name}" WHERE tenant_id=:t'), {"t": tid})).scalar() or 0
        if "is_sample" in table.c:
            mau += (await a.execute(text(f'SELECT count(*) FROM "{table.name}" WHERE tenant_id=:t AND is_sample'), {"t": tid})).scalar() or 0
    return {"tong_ban_ghi": tong, "ban_ghi_minh_hoa": mau}


def _tenant_out(t: Tenant) -> dict:
    cfg = t.config or {}
    return {"id": t.id, "ma_dvhc": t.ma_dvhc, "ten": t.ten, "cap": t.cap, "parent_id": t.parent_id, "trang_thai": t.trang_thai,
            "ten_co_quan": cfg.get("ten_co_quan") or [], "ban_do": cfg.get("ban_do") or {}, "modules": t.modules or {},
            "slug": cfg.get("slug"), "ten_mien": cfg.get("ten_mien") or []}


@router.get("/{tid}")
async def get_tenant(tid: int, _: CurrentUser = Depends(PLATFORM)) -> dict:
    async with admin_sessionmaker()() as a:
        t = await _unit(a, tid)
        n_users = (await a.execute(text("SELECT count(*) FROM app_user WHERE tenant_id=:t"), {"t": tid})).scalar()
        return {**_tenant_out(t), **await _counts(a, tid), "so_nguoi_dung": n_users}


class TenantPatch(BaseModel):
    ten: str | None = Field(None, min_length=1, max_length=200)
    parent_id: int | None = None
    ten_co_quan: list[str] | None = None
    tam: list[float] | None = Field(None, min_length=2, max_length=2)
    zoom: int | None = Field(None, ge=8, le=19)
    modules: dict[str, str] | None = None
    slug: str | None = Field(None, max_length=40)
    ten_mien: list[str] | None = Field(None, max_length=5)


RESERVED_SLUGS = {"quan-tri", "xac-dinh", "api", "p", "dang-nhap"}


async def _check_public_address(a, tid: int, slug: str | None, domains: list[str] | None) -> tuple[str | None, list[str] | None]:  # noqa: ANN001
    """Địa chỉ công khai: mã đường dẫn (/p/<mã>) và tên miền riêng — không được trùng với đơn vị khác."""
    from app.cong_khai.service import HOST_RE, SLUG_RE, norm_host

    if slug is not None:
        slug = slug.strip().lower()
        if slug and (not SLUG_RE.match(slug) or slug in RESERVED_SLUGS):
            raise HTTPException(422, "Mã đường dẫn chỉ gồm chữ thường không dấu, số và dấu gạch ngang (VD viet-yen)")
    if domains is not None:
        domains = list(dict.fromkeys(norm_host(d.replace("https://", "").replace("http://", "").split("/")[0]) for d in domains if d.strip()))
        bad = [d for d in domains if not HOST_RE.match(d)]
        if bad:
            raise HTTPException(422, f"Tên miền không hợp lệ: {', '.join(bad)}")
    others = list((await a.execute(select(Tenant).where(Tenant.id != tid))).scalars())
    for o in others:
        ocfg = o.config or {}
        if slug and ocfg.get("slug") == slug:
            raise HTTPException(409, f"Mã đường dẫn “{slug}” đã dùng cho {o.ten}")
        dup = set(domains or []) & set(ocfg.get("ten_mien") or [])
        if dup:
            raise HTTPException(409, f"Tên miền {', '.join(sorted(dup))} đã gắn cho {o.ten}")
    return slug, domains


@router.patch("/{tid}")
async def patch_tenant(tid: int, body: TenantPatch, user: CurrentUser = Depends(PLATFORM)) -> dict:
    async with admin_sessionmaker()() as a:
        t = await _unit(a, tid)
        before = _tenant_out(t)
        if body.ten is not None:
            t.ten = body.ten.strip()
            for u in (await a.execute(select(User).where(User.tenant_id == tid, User.don_vi == before["ten"]))).scalars():
                u.don_vi = t.ten
        if body.parent_id is not None:
            p = await a.get(Tenant, body.parent_id)
            if p is None or p.cap != "tinh":
                raise HTTPException(422, "Đơn vị cấp trên phải là tỉnh/thành phố")
            t.parent_id = p.id
        cfg = dict(t.config or {})
        if body.slug is not None or body.ten_mien is not None:
            slug, domains = await _check_public_address(a, tid, body.slug, body.ten_mien)
            if body.slug is not None:
                cfg["slug"] = slug or None
            if body.ten_mien is not None:
                cfg["ten_mien"] = domains
        if body.ten_co_quan is not None:
            cfg["ten_co_quan"] = [x.strip() for x in body.ten_co_quan if x.strip()][:2]
        if body.tam is not None or body.zoom is not None:
            bd = dict(cfg.get("ban_do") or {})
            if body.tam is not None:
                lat, lng = body.tam
                if not (8 <= lat <= 24 and 102 <= lng <= 110):
                    raise HTTPException(422, "Tọa độ tâm bản đồ phải nằm trong lãnh thổ Việt Nam")
                bd["tam"] = [lat, lng]
                bd["bbox"] = [round(lat - 0.025, 4), round(lng - 0.035, 4), round(lat + 0.025, 4), round(lng + 0.035, 4)]
            if body.zoom is not None:
                bd["zoom"] = body.zoom
            cfg["ban_do"] = bd
        t.config = cfg
        if body.modules is not None:
            bad = [k for k, v in body.modules.items() if k not in PHAN_HE or v not in ("bat", "tat")]
            if bad:
                raise HTTPException(422, f"Phân hệ không hợp lệ: {', '.join(bad)}")
            t.modules = {**(t.modules or {}), **body.modules}
        await a.commit()
        after = _tenant_out(t)
    await record_change(user, tid, f"don_vi:{tid}:sua", before, after)
    return after


class StatusIn(BaseModel):
    trang_thai: str = Field(pattern="^(hoat_dong|tam_dung)$")
    ly_do: str = ""


@router.post("/{tid}/trang-thai")
async def set_status(tid: int, body: StatusIn, user: CurrentUser = Depends(PLATFORM)) -> dict:
    """Tạm dừng: mọi tài khoản của đơn vị bị đăng xuất và không đăng nhập được; dữ liệu giữ nguyên."""
    if body.trang_thai == "tam_dung" and not body.ly_do.strip():
        raise HTTPException(422, "Ghi rõ lý do tạm dừng")
    async with admin_sessionmaker()() as a:
        t = await _unit(a, tid)
        before = t.trang_thai
        t.trang_thai = body.trang_thai
        if body.trang_thai == "tam_dung":
            for u in (await a.execute(select(User).where(User.tenant_id == tid))).scalars():
                u.token_version += 1
        await a.commit()
    await record_change(user, tid, f"don_vi:{tid}:trang_thai", {"trang_thai": before}, {"trang_thai": body.trang_thai, "ly_do": body.ly_do})
    return {"trang_thai": body.trang_thai}


class DeleteIn(BaseModel):
    xac_nhan: str


@router.delete("/{tid}")
async def delete_tenant(tid: int, body: DeleteIn, user: CurrentUser = Depends(PLATFORM)) -> dict:
    """Xóa vĩnh viễn đơn vị và toàn bộ dữ liệu, tài khoản. Chỉ khi đơn vị đã tạm dừng; gõ đúng mã ĐVHC để xác nhận.
    Nhật ký truy cập được giữ lại (chỉ ghi thêm)."""
    import_models()
    async with admin_sessionmaker()() as a:
        t = await _unit(a, tid)
        if t.trang_thai != "tam_dung":
            raise HTTPException(409, "Tạm dừng đơn vị trước khi xóa")
        if body.xac_nhan != t.ma_dvhc:
            raise HTTPException(422, f"Gõ chính xác mã đơn vị '{t.ma_dvhc}' để xác nhận xóa")
        if (await a.execute(select(Tenant.id).where(Tenant.parent_id == tid))).first():
            raise HTTPException(409, "Đơn vị còn đơn vị cấp dưới")
        info = {"ma_dvhc": t.ma_dvhc, "ten": t.ten}
        n = 0
        for table in reversed(Base.metadata.sorted_tables):
            if "tenant_id" in table.c and table.name != "audit_log" and not table.info.get("append_only") and table.name != "tenant":
                r = await a.execute(text(f'DELETE FROM "{table.name}" WHERE tenant_id = :t'), {"t": tid})
                n += r.rowcount or 0
        await a.delete(t)
        await a.commit()
    await record_change(user, None, f"don_vi:{tid}:xoa", info, {"da_xoa_ban_ghi": n})
    return {"da_xoa": n, **info}


@router.post("/{tid}/vao-quan-tri")
async def enter_tenant(tid: int, user: CurrentUser = Depends(PLATFORM)) -> dict:
    """Quản trị nền tảng vào quản trị toàn bộ nội dung của một xã/phường: cấp phiên riêng gắn với đơn vị đó.
    Mọi thao tác trong phiên được ghi nhật ký của đơn vị với tài khoản quản trị nền tảng."""
    from app.auth.security import make_token

    if user.dai_dien:
        raise HTTPException(409, "Đang trong phiên quản trị đơn vị khác; thoát trước")
    async with admin_sessionmaker()() as a:
        t = await _unit(a, tid)
        if t.trang_thai != "hoat_dong":
            raise HTTPException(409, "Đơn vị đang tạm dừng; kích hoạt trước khi vào quản trị")
        u = await a.get(User, user.id)
        token, ten = make_token(u.id, u.token_version, act=tid), t.ten
    await record_change(user, tid, f"don_vi:{tid}:vao_quan_tri", None, {"boi": user.username})
    return {"access_token": token, "token_type": "bearer", "don_vi": ten}


# ---------------- Tài khoản của đơn vị ----------------
@router.get("/{tid}/users")
async def unit_users(tid: int, _: CurrentUser = Depends(PLATFORM)) -> list:
    async with admin_sessionmaker()() as a:
        await _unit(a, tid)
        us = list((await a.execute(select(User).where(User.tenant_id == tid).order_by(User.ho_ten))).scalars())
        gs = list((await a.execute(select(Grant).where(Grant.user_id.in_([u.id for u in us])))).scalars()) if us else []
    return [_user_out(u, [g for g in gs if g.user_id == u.id]) for u in us]


class UnitUserIn(Leader):
    role: str
    nhom: list[str] | None = None
    don_vi: str | None = None


def _check_role(role: str, nhom: list[str] | None) -> list:
    if role not in UNIT_CREATABLE:
        raise HTTPException(422, "Vai trò không hợp lệ cho tài khoản của xã/phường")
    try:
        return default_grants(role, nhom)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.post("/{tid}/users", status_code=201)
async def add_unit_user(tid: int, body: UnitUserIn, user: CurrentUser = Depends(PLATFORM)) -> dict:
    """Nền tảng cấp tài khoản trực tiếp (VD quản trị đơn vị đầu tiên, hoặc khi đơn vị mất hết tài khoản quản trị)."""
    _check_role(body.role, body.nhom)
    async with admin_sessionmaker()() as a:
        t = await _unit(a, tid)
        u, pw, secret = await _new_user(a, tid, body, body.role, body.nhom)
        u.don_vi = body.don_vi or t.ten
        await a.commit()
        out = {"id": u.id, "username": u.username, "mat_khau_tam": pw, "totp_secret": secret,
               "ghi_chu": "Mật khẩu tạm và mã 2 lớp chỉ hiển thị một lần; người dùng phải đổi mật khẩu khi đăng nhập lần đầu"}
    await record_change(user, tid, f"nguoi_dung:{u.id}:tao", None, {"username": u.username, "role": body.role, "boi": "nen_tang"})
    return out


class UnitUserPatch(BaseModel):
    ho_ten: str | None = Field(None, min_length=1)
    chuc_danh: str | None = None
    role: str | None = None
    nhom: list[str] | None = None
    trang_thai: str | None = Field(None, pattern="^(hoat_dong|thu_hoi)$")
    ly_do: str = ""


async def _member(a, tid: int, uid: int) -> User:  # noqa: ANN001
    u = await a.get(User, uid)
    if u is None or u.tenant_id != tid:
        raise HTTPException(404, "Không tìm thấy tài khoản của đơn vị")
    return u


@router.patch("/{tid}/users/{uid}")
async def patch_unit_user(tid: int, uid: int, body: UnitUserPatch, user: CurrentUser = Depends(PLATFORM)) -> dict:
    async with admin_sessionmaker()() as a:
        await _unit(a, tid)
        u = await _member(a, tid, uid)
        gs = list((await a.execute(select(Grant).where(Grant.user_id == uid))).scalars())
        before = _user_out(u, gs)
        if body.ho_ten is not None:
            u.ho_ten = body.ho_ten.strip()
        if body.chuc_danh is not None:
            u.chuc_danh = body.chuc_danh.strip()
        if body.role is not None:
            grants = _check_role(body.role, body.nhom)
            for g in gs:
                await a.delete(g)
            for g_nhom, g_quyen in grants:
                a.add(Grant(user_id=uid, tenant_id=tid, role=body.role, nhom_du_lieu=g_nhom, quyen=g_quyen))
            u.token_version += 1
        if body.trang_thai is not None and body.trang_thai != u.trang_thai:
            if body.trang_thai == "thu_hoi":
                if not body.ly_do.strip():
                    raise HTTPException(422, "Ghi rõ lý do thu hồi tài khoản")
                u.trang_thai, u.ly_do_thu_hoi = "thu_hoi", body.ly_do.strip()
            else:
                u.trang_thai, u.ly_do_thu_hoi = "hoat_dong", None
            u.token_version += 1
        await a.commit()
        gs = list((await a.execute(select(Grant).where(Grant.user_id == uid))).scalars())
        after = _user_out(u, gs)
    await record_change(user, tid, f"nguoi_dung:{uid}:sua", before, after)
    return after


@router.post("/{tid}/users/{uid}/reset-password")
async def reset_unit_password(tid: int, uid: int, user: CurrentUser = Depends(PLATFORM)) -> dict:
    pw = temp_password()
    async with admin_sessionmaker()() as a:
        u = await _member(a, tid, uid)
        u.password_hash, u.phai_doi_mat_khau = hash_password(pw), True
        u.failed_count, u.locked_until = 0, None
        u.token_version += 1
        await a.commit()
        name = u.username
    await record_change(user, tid, f"nguoi_dung:{uid}:dat_lai_mat_khau", None, {"boi": "nen_tang"})
    return {"username": name, "mat_khau_tam": pw, "ghi_chu": "Mật khẩu tạm chỉ hiển thị một lần"}


@router.delete("/{tid}/users/{uid}")
async def delete_unit_user(tid: int, uid: int, user: CurrentUser = Depends(PLATFORM)) -> dict:
    """Xóa hẳn chỉ áp dụng tài khoản đã thu hồi (tài khoản đang dùng phải thu hồi trước để lưu vết)."""
    async with admin_sessionmaker()() as a:
        u = await _member(a, tid, uid)
        if u.trang_thai != "thu_hoi":
            raise HTTPException(409, "Thu hồi tài khoản trước khi xóa")
        name = u.username
        await a.delete(u)
        await a.commit()
    await record_change(user, tid, f"nguoi_dung:{uid}:xoa", {"username": name}, None)
    return {"ok": True}


# ---------------- Dữ liệu minh họa ----------------
@router.post("/{tid}/du-lieu-minh-hoa")
async def seed_sample(tid: int, user: CurrentUser = Depends(PLATFORM)) -> dict:
    """Nạp (hoặc nạp lại) bộ dữ liệu minh họa cho đơn vị: số liệu, phản ánh, cơ cấu tổ chức, dự án… gắn cờ minh họa."""
    from seeds.run import seed_sample_for

    async with admin_sessionmaker()() as a:
        t = await _unit(a, tid)
        if not (await a.execute(select(User.id).where(User.tenant_id == tid, User.trang_thai == "hoat_dong"))).first():
            raise HTTPException(409, "Đơn vị chưa có tài khoản đang hoạt động")
        ten = t.ten
    try:
        out = await seed_sample_for(tid)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    await record_change(user, tid, f"don_vi:{tid}:nap_minh_hoa", None, {"so_ban_ghi": out["so_ban_ghi"]})
    return {"don_vi": ten, **out}


@router.delete("/{tid}/du-lieu-minh-hoa")
async def purge_sample(tid: int, user: CurrentUser = Depends(PLATFORM)) -> dict:
    from seeds.run import purge_sample_by_id

    async with admin_sessionmaker()() as a:
        await _unit(a, tid)
        n = await purge_sample_by_id(a, tid)
        await a.commit()
    await record_change(user, tid, f"don_vi:{tid}:xoa_minh_hoa", None, {"da_xoa": n})
    return {"da_xoa": n}
