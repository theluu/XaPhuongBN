"""Trang công khai theo phường (không cần đăng nhập) và phần quản trị công khai (lãnh đạo chọn chỉ tiêu, công bố kỳ)."""
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, tenant_db
from app.auth.models import User
from app.catalog.models import Indicator
from app.cong_khai.models import CongBo
from app.cong_khai.service import CHUYEN_MUC, PHUC_VU_MAC_DINH, compare_row, TEN_PHAN_HE, TONG_HOP, build_snapshot, norm_host, public_config, tenant_for_host, tenant_for_slug, ward_card, wards
from app.core.db import admin_sessionmaker
from app.core.json import jsonable
from app.core.periods import parse_ky
from app.core.principal import CurrentUser
from app.platform.models import Tenant

router = APIRouter(prefix="/api/cong-khai", tags=["cong-khai"])
SUA_CAU_HINH = {"lanh_dao", "quan_tri_don_vi"}
CONG_BO = {"lanh_dao"}


def request_host(request: Request) -> str:
    return norm_host(request.headers.get("x-forwarded-host") or request.headers.get("host"))


def _has(user: CurrentUser, roles: set[str]) -> bool:
    return bool(user.roles & roles)


async def _latest(adm: AsyncSession, tid: int, ky: str | None = None) -> CongBo | None:
    q = select(CongBo).where(CongBo.tenant_id == tid, CongBo.thu_hoi_luc.is_(None))
    if ky:
        q = q.where(CongBo.ky == ky)
    return (await adm.execute(q.order_by(CongBo.cong_bo_luc.desc(), CongBo.id.desc()).limit(1))).scalar()


def _ban_out(b: CongBo) -> dict:
    return {"id": b.id, "ky": b.ky, "cong_bo_luc": b.cong_bo_luc, "nguoi_cong_bo": b.nguoi_cong_bo_ten, "thu_hoi_luc": b.thu_hoi_luc,
            "thong_ke": (b.du_lieu or {}).get("thong_ke"), "co_minh_hoa": bool((b.du_lieu or {}).get("co_minh_hoa"))}


# ───────────────────────── Quản trị công khai (cần đăng nhập) ─────────────────────────

@router.get("/quan-tri")
async def admin_get(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    tid = s.info["tenant_id"]
    t = await s.get(Tenant, tid)
    inds = list((await s.execute(select(Indicator).where(Indicator.tenant_id == tid).order_by(Indicator.ma_chi_tieu))).scalars())
    cfg = public_config(t, inds)
    async with admin_sessionmaker()() as adm:
        ds = list((await adm.execute(select(CongBo).where(CongBo.tenant_id == tid).order_by(CongBo.cong_bo_luc.desc()).limit(30))).scalars())
    w = ward_card(t)
    return jsonable({
        "cau_hinh": cfg, "don_vi": w,
        "duong_dan": [f"https://{d}" for d in w["ten_mien"]] + ([f"/p/{w['slug']}"] if w["slug"] else []),
        "chi_tieu": [{"ma": i.ma_chi_tieu, "ten": i.ten, "phan_he": i.phan_he, "ten_phan_he": TEN_PHAN_HE.get(i.phan_he, "Khác"),
                      "don_vi": i.don_vi_do, "phan_loai_thong_tin": i.phan_loai_thong_tin, "bo": i.bo or []} for i in inds],
        "tong_hop": [{"ma": k, "ten": v} for k, v in TONG_HOP.items()],
        "chuyen_muc": [{"ma": k, "ten": v} for k, v in CHUYEN_MUC.items()],
        "lich_su": [_ban_out(b) for b in ds],
        "quyen": {"sua": _has(user, SUA_CAU_HINH), "cong_bo": _has(user, CONG_BO)},
    })


class ConfigIn(BaseModel):
    chi_tieu: list[str] = Field(default_factory=list, max_length=200)
    tong_hop: list[str] = Field(default_factory=list, max_length=20)
    xu_huong_ngan_sach: bool = True
    chuyen_muc: list[str] | None = Field(None, max_length=20)
    gioi_thieu: str = Field("", max_length=600)


@router.put("/quan-tri")
async def admin_put(body: ConfigIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    if not _has(user, SUA_CAU_HINH):
        raise HTTPException(403, "Chỉ lãnh đạo hoặc quản trị đơn vị được chọn chỉ tiêu công khai")
    tid = s.info["tenant_id"]
    inds = {i.ma_chi_tieu: i for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tid))).scalars()}
    bad = [m for m in body.chi_tieu if m not in inds]
    if bad:
        raise HTTPException(422, f"Chỉ tiêu không tồn tại: {', '.join(bad[:5])}")
    restricted = [m for m in body.chi_tieu if inds[m].phan_loai_thong_tin == "han_che"]
    if restricted:
        raise HTTPException(422, f"Chỉ tiêu phân loại hạn chế không được công khai: {', '.join(restricted[:5])}")
    bad = [m for m in body.tong_hop if m not in TONG_HOP]
    if bad:
        raise HTTPException(422, f"Ô tổng hợp không hợp lệ: {', '.join(bad)}")
    bad = [m for m in body.chuyen_muc or [] if m not in CHUYEN_MUC]
    if bad:
        raise HTTPException(422, f"Chuyên mục không hợp lệ: {', '.join(bad)}")
    async with admin_sessionmaker()() as adm:
        t = await adm.get(Tenant, tid)
        before = (t.config or {}).get("cong_khai")
        new = {"chi_tieu": list(dict.fromkeys(body.chi_tieu)), "tong_hop": list(dict.fromkeys(body.tong_hop)),
               "xu_huong_ngan_sach": body.xu_huong_ngan_sach, "gioi_thieu": body.gioi_thieu.strip(),
               "chuyen_muc": list(dict.fromkeys(body.chuyen_muc)) if body.chuyen_muc is not None else list(CHUYEN_MUC)}
        t.config = {**(t.config or {}), "cong_khai": new}
        await adm.commit()
    await record_change(user, tid, "cong_khai:cau_hinh", before, new)
    return new


KY_RE = r"^\d{4}(-(0[1-9]|1[0-2])|-Q[1-4])?$"


class KyIn(BaseModel):
    ky: str = Field(pattern=KY_RE)


@router.post("/quan-tri/xem-truoc")
async def admin_preview(body: KyIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    if not _has(user, SUA_CAU_HINH):
        raise HTTPException(403, "Bạn không có quyền xem trước trang công khai")
    parse_ky(body.ky)
    return await build_snapshot(s.info["tenant_id"], body.ky)


@router.post("/quan-tri/cong-bo")
async def admin_publish(body: KyIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    """Lãnh đạo công bố kỳ: chụp số liệu đã xác nhận của các chỉ tiêu được chọn → trang công khai hiển thị bản này."""
    if not _has(user, CONG_BO):
        raise HTTPException(403, "Chỉ lãnh đạo phường được công bố số liệu ra trang công khai")
    parse_ky(body.ky)
    tid = s.info["tenant_id"]
    snap = await build_snapshot(tid, body.ky)
    async with admin_sessionmaker()() as adm:
        u = await adm.get(User, user.id)
        b = CongBo(tenant_id=tid, ky=body.ky, du_lieu=snap, nguoi_cong_bo_id=user.id, nguoi_cong_bo_ten=(u.ho_ten if u else user.username),
                   is_sample=bool(snap.get("co_minh_hoa")))
        adm.add(b)
        await adm.commit()
        out = _ban_out(b)
    await record_change(user, tid, f"cong_khai:cong_bo:{body.ky}", None, jsonable(out))
    return jsonable(out)


class ThuHoiIn(BaseModel):
    ly_do: str = Field(min_length=3, max_length=500)


@router.post("/quan-tri/{bid}/thu-hoi")
async def admin_retract(bid: int, body: ThuHoiIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    if not _has(user, CONG_BO):
        raise HTTPException(403, "Chỉ lãnh đạo phường được thu hồi bản công bố")
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as adm:
        b = await adm.get(CongBo, bid)
        if b is None or b.tenant_id != tid:
            raise HTTPException(404, "Không tìm thấy bản công bố")
        if b.thu_hoi_luc is None:
            b.thu_hoi_luc = datetime.now(UTC)
            await adm.commit()
        out = _ban_out(b)
    await record_change(user, tid, f"cong_khai:thu_hoi:{b.ky}", None, {**jsonable(out), "ly_do": body.ly_do})
    return jsonable(out)


class TieuChiIn(BaseModel):
    ten: str = Field(min_length=1, max_length=120)
    diem: float = Field(ge=0, le=100)
    toi_da: float = Field(gt=0, le=100)


class PhucVuIn(BaseModel):
    ky: str = Field(pattern=r"^\d{4}-\d{2}$")
    tieu_chi: list[TieuChiIn] = Field(min_length=1, max_length=10)
    xep_hang: int | None = Field(None, ge=1, le=10000)
    tong_don_vi: int | None = Field(None, ge=1, le=10000)


@router.get("/quan-tri/chi-so-phuc-vu")
async def phuc_vu_get(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    t = await s.get(Tenant, s.info["tenant_id"])
    return {"mac_dinh": [{"ten": a, "toi_da": b} for a, b in PHUC_VU_MAC_DINH], "du_lieu": (t.config or {}).get("chi_so_phuc_vu") or {}}


@router.put("/quan-tri/chi-so-phuc-vu")
async def phuc_vu_put(body: PhucVuIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    """Nhập kết quả Bộ chỉ số phục vụ người dân của một tháng (theo kết quả đánh giá được cấp có thẩm quyền công bố)."""
    if not _has(user, SUA_CAU_HINH):
        raise HTTPException(403, "Chỉ lãnh đạo hoặc quản trị đơn vị được nhập chỉ số phục vụ")
    bad = [x.ten for x in body.tieu_chi if x.diem > x.toi_da]
    if bad:
        raise HTTPException(422, f"Điểm vượt điểm tối đa: {', '.join(bad)}")
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as adm:
        t = await adm.get(Tenant, tid)
        data = dict((t.config or {}).get("chi_so_phuc_vu") or {})
        before = data.get(body.ky)
        data[body.ky] = {"tieu_chi": [x.model_dump() for x in body.tieu_chi], "xep_hang": body.xep_hang, "tong_don_vi": body.tong_don_vi}
        t.config = {**(t.config or {}), "chi_so_phuc_vu": data}
        await adm.commit()
    await record_change(user, tid, f"cong_khai:chi_so_phuc_vu:{body.ky}", before, data[body.ky])
    return data[body.ky]


# ───────────────────────── Công khai (không cần đăng nhập) ─────────────────────────

@router.get("/xac-dinh")
async def resolve(request: Request) -> dict:
    """Tên miền đang truy cập thuộc phường nào (null = tên miền chung của nền tảng)."""
    async with admin_sessionmaker()() as adm:
        t = await tenant_for_host(adm, request_host(request))
    return {"don_vi": ward_card(t) if t else None}


@router.get("")
async def list_public() -> dict:
    """Trang chung: các phường đang dùng nền tảng và số liệu đã công bố gần nhất."""
    out, cmp = [], []
    async with admin_sessionmaker()() as adm:
        for t in await wards(adm):
            w = ward_card(t)
            if not w["slug"]:
                continue
            b = await _latest(adm, t.id)
            out.append({**w, "ban_moi_nhat": _ban_out(b) if b else None,
                        "noi_bat": ((b.du_lieu or {}).get("tong_hop") or [])[:3] if b else []})
            if b:
                cmp.append({**compare_row(t, b.du_lieu), "ky": b.ky, "co_minh_hoa": bool((b.du_lieu or {}).get("co_minh_hoa"))})
    return jsonable({"don_vi": out, "so_sanh": cmp})


@router.get("/{slug}")
async def public_page(slug: str, ky: str | None = Query(None, pattern=KY_RE)) -> dict:
    async with admin_sessionmaker()() as adm:
        t = await tenant_for_slug(adm, slug)
        if t is None:
            raise HTTPException(404, "Không tìm thấy đơn vị")
        b = await _latest(adm, t.id, ky)
        kys = sorted({k for k in (await adm.execute(select(CongBo.ky).where(CongBo.tenant_id == t.id, CongBo.thu_hoi_luc.is_(None)))).scalars()},
                     reverse=True)
    return jsonable({"don_vi": ward_card(t), "ky_da_cong_bo": kys, "ban": {**_ban_out(b), "du_lieu": b.du_lieu} if b else None,
                     "hom_nay": date.today()})
