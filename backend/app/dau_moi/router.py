"""Đầu mối & trách nhiệm chủ trì/phối hợp (DT V.1): ai chủ trì, ai phối hợp, ai cung cấp – xác nhận số liệu gì,
liên hệ thế nào, tài khoản nào trên hệ thống, đang trễ hạn gì."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, require, tenant_db
from app.auth.models import Grant, User
from app.compliance.service import reminders
from app.core.db import admin_sessionmaker
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.dau_moi.models import DauMoi
from app.dau_moi.service import CAP, NHOM_TN, PHIEU, PHIEU_TOI_THIEU, TOI_THIEU_CHUNG, VAI_TRO, ensure
from app.platform.models import Tenant

router = APIRouter(prefix="/api/dau-moi", tags=["dau-moi"])
WRITE = require("duyet", "quan_tri")


async def _rows(s: AsyncSession) -> list[DauMoi]:
    tid = s.info["tenant_id"]
    t = await s.get(Tenant, tid)
    return await ensure(s, tid, t.ten if t else "đơn vị")


async def _accounts(ids: set[int]) -> dict[int, dict]:
    if not ids:
        return {}
    async with admin_sessionmaker()() as a:
        us = list((await a.execute(select(User).where(User.id.in_(ids)))).scalars())
        gs = list((await a.execute(select(Grant).where(Grant.user_id.in_(ids)))).scalars())
    return {u.id: {"id": u.id, "username": u.username, "ho_ten": u.ho_ten, "chuc_danh": u.chuc_danh, "trang_thai": u.trang_thai,
                   "roles": sorted({g.role for g in gs if g.user_id == u.id}),
                   "nhom": sorted({n for g in gs if g.user_id == u.id for n in (g.nhom_du_lieu or ["*"])})} for u in us}


def _out(d: DauMoi, acc: dict[int, dict], viec: list[dict], hide: bool) -> dict:
    return {
        "id": d.id, "ma": d.ma, "ten": d.ten, "cap": d.cap, "cap_ten": CAP.get(d.cap, d.cap), "noi_dung": d.noi_dung,
        "trach_nhiem": [{**t, "vai_tro_ten": VAI_TRO.get(t["vai_tro"], t["vai_tro"])} for t in d.trach_nhiem or []],
        "phieu_nguon": [{"ma": p, "ten": PHIEU.get(p, p), "toi_thieu": PHIEU_TOI_THIEU.get(p, "")} for p in d.phieu_nguon or []], "chi_tieu": d.chi_tieu or [], "nguon": d.nguon or [],
        "nguoi_lien_he": d.nguoi_lien_he, "chuc_vu": d.chuc_vu, "dien_thoai": None if hide else d.dien_thoai, "email": None if hide else d.email,
        "tai_khoan": [acc[i] for i in d.user_ids or [] if i in acc and not hide], "thu_tu": d.thu_tu, "is_sample": d.is_sample,
        "viec_tre": viec, "so_qua_han": sum(1 for v in viec if v["muc"] == "qua_han"),
    }


def _by_dau_moi(rem: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rem:
        for d in r.get("dau_moi", []):
            out.setdefault(d["ma"], []).append({k: r[k] for k in ("ma", "ten", "ky", "han", "con_lai_ngay", "muc")})
    return out


@router.get("")
async def list_dau_moi(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    rows = await _rows(s)
    await s.commit()
    hide = "man_hinh_tv" in user.roles
    acc = await _accounts({i for d in rows for i in d.user_ids or []})
    viec = _by_dau_moi(await reminders(s, s.info["tenant_id"], date.today(), None))
    return jsonable({"dau_moi": [_out(d, acc, viec.get(d.ma, []), hide) for d in rows], "vai_tro": VAI_TRO, "cap": CAP, "phieu": PHIEU,
                     "nhom": NHOM_TN, "toi_thieu_chung": TOI_THIEU_CHUNG, "cua_toi": [d.ma for d in rows if user.id in (d.user_ids or [])]})


class TrachNhiem(BaseModel):
    nhom: str
    vai_tro: str
    noi_dung: str = ""


class DauMoiIn(BaseModel):
    ma: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_.-]+$")
    ten: str = Field(min_length=1, max_length=300)
    cap: str = Field(pattern="^(phuong|thanh_pho|chuyen_nganh|chu_dau_tu)$")
    noi_dung: str = ""
    trach_nhiem: list[TrachNhiem] = []
    phieu_nguon: list[str] = []
    chi_tieu: list[str] = []
    nguon: list[str] = []
    nguoi_lien_he: str = ""
    chuc_vu: str = ""
    dien_thoai: str | None = Field(None, max_length=30)
    email: str | None = Field(None, max_length=200)
    user_ids: list[int] = []
    thu_tu: int | None = None


async def _validate(s: AsyncSession, body: DauMoiIn) -> None:
    from app.catalog.models import Indicator

    tid = s.info["tenant_id"]
    for t in body.trach_nhiem:
        if t.nhom not in NHOM_TN or t.vai_tro not in VAI_TRO:
            raise HTTPException(422, f"Trách nhiệm không hợp lệ: {t.nhom}/{t.vai_tro}")
    bad = [p for p in body.phieu_nguon if p not in PHIEU]
    if bad:
        raise HTTPException(422, f"Mục phiếu nguồn không hợp lệ: {', '.join(bad)}")
    if body.chi_tieu:
        have = set((await s.execute(select(Indicator.ma_chi_tieu).where(Indicator.tenant_id == tid, Indicator.ma_chi_tieu.in_(body.chi_tieu)))).scalars())
        miss = [m for m in body.chi_tieu if m not in have]
        if miss:
            raise HTTPException(422, f"Không có chỉ tiêu: {', '.join(miss)}")
    if body.user_ids:
        async with admin_sessionmaker()() as a:
            us = list((await a.execute(select(User).where(User.id.in_(body.user_ids)))).scalars())
            nen_tang = set((await a.execute(select(Grant.user_id).where(Grant.user_id.in_(body.user_ids), Grant.role == "quan_tri_nen_tang"))).scalars())
        ok = {u.id for u in us if u.tenant_id == tid or u.id in nen_tang}
        if set(body.user_ids) - ok:
            raise HTTPException(422, "Chỉ gắn tài khoản của đơn vị (hoặc tài khoản quản trị nền tảng)")


def _apply(d: DauMoi, body: DauMoiIn) -> None:
    d.ma, d.ten, d.cap, d.noi_dung = body.ma.strip().upper(), body.ten.strip(), body.cap, body.noi_dung.strip()
    d.trach_nhiem = [t.model_dump() for t in body.trach_nhiem]
    d.phieu_nguon, d.chi_tieu, d.nguon = sorted(set(body.phieu_nguon)), list(dict.fromkeys(body.chi_tieu)), list(dict.fromkeys(body.nguon))
    d.nguoi_lien_he, d.chuc_vu = body.nguoi_lien_he.strip(), body.chuc_vu.strip()
    d.dien_thoai, d.email = (body.dien_thoai or "").strip() or None, (body.email or "").strip() or None
    d.user_ids = list(dict.fromkeys(body.user_ids))
    if body.thu_tu is not None:
        d.thu_tu = body.thu_tu


def _snap(d: DauMoi) -> dict:
    return {"ma": d.ma, "ten": d.ten, "cap": d.cap, "trach_nhiem": d.trach_nhiem, "chi_tieu": d.chi_tieu, "user_ids": d.user_ids,
            "nguoi_lien_he": d.nguoi_lien_he, "dien_thoai": d.dien_thoai}


@router.post("", status_code=201)
async def add_dau_moi(body: DauMoiIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(WRITE)) -> dict:
    rows = await _rows(s)
    if any(d.ma == body.ma.strip().upper() for d in rows):
        raise HTTPException(409, "Mã đầu mối đã có")
    await _validate(s, body)
    d = DauMoi(tenant_id=s.info["tenant_id"], thu_tu=max([x.thu_tu for x in rows], default=0) + 1)
    _apply(d, body)
    s.add(d)
    await s.commit()
    await record_change(user, d.tenant_id, f"dau_moi:{d.ma}:tao", None, _snap(d))
    return {"id": d.id, "ma": d.ma}


@router.put("/{ma}")
async def put_dau_moi(ma: str, body: DauMoiIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(WRITE)) -> dict:
    rows = await _rows(s)
    d = next((x for x in rows if x.ma == ma), None)
    if d is None:
        raise HTTPException(404, "Không tìm thấy đầu mối")
    if body.ma.strip().upper() != ma and any(x.ma == body.ma.strip().upper() for x in rows):
        raise HTTPException(409, "Mã đầu mối đã có")
    await _validate(s, body)
    before = _snap(d)
    _apply(d, body)
    await s.commit()
    await record_change(user, d.tenant_id, f"dau_moi:{d.ma}:sua", before, _snap(d))
    return {"id": d.id, "ma": d.ma}


@router.delete("/{ma}")
async def delete_dau_moi(ma: str, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(WRITE)) -> dict:
    rows = await _rows(s)
    d = next((x for x in rows if x.ma == ma), None)
    if d is None:
        raise HTTPException(404, "Không tìm thấy đầu mối")
    if len(rows) == 1:
        raise HTTPException(409, "Phải còn ít nhất một đầu mối")
    before = _snap(d)
    await s.delete(d)
    await s.commit()
    await record_change(user, s.info["tenant_id"], f"dau_moi:{ma}:xoa", before, None)
    return {"ok": True}
