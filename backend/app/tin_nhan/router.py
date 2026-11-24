"""Nhắn tin nội bộ và gửi tệp, công văn xử lý — gắn với cảnh báo/phản ánh để khi phát hiện chỉ số có cảnh báo
lãnh đạo nhắn ngay cho người phụ trách và gửi kèm công văn chỉ đạo.

Phạm vi: chỉ cán bộ cùng đơn vị (RLS); chỉ thành viên hội thoại đọc được tin và tải được tệp; tài khoản màn hình TV
không nhắn tin; công văn do lãnh đạo/quản trị phát hành, đồng thời vào sổ Văn bản chỉ đạo điều hành."""
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, tenant_db
from app.auth.models import Grant, User
from app.core.db import admin_sessionmaker
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.files import storage
from app.files.models import StoredFile
from app.tin_nhan.models import HoiThoai, TepTinNhan, ThanhVien, TinNhan

router = APIRouter(prefix="/api/tin-nhan", tags=["tin-nhan"])
TOI_DA_TEP = 10


def _check(user: CurrentUser) -> None:
    if "man_hinh_tv" in user.roles:
        raise HTTPException(403, "Tài khoản màn hình TV không dùng nhắn tin")


def can_issue(user: CurrentUser) -> bool:
    """Phát hành công văn xử lý: lãnh đạo (duyệt cảnh báo/nhiệm vụ) hoặc quản trị đơn vị."""
    return user.can("duyet", "canh_bao") or user.can("duyet", "quan_tri")


async def _people(tid: int, ids: set[int] | None = None) -> dict[int, dict]:
    """Danh bạ cán bộ của đơn vị (không gồm tài khoản màn hình TV, tài khoản đã thu hồi)."""
    async with admin_sessionmaker()() as a:
        q = select(User).where(User.tenant_id == tid)
        if ids is not None:
            q = q.where(User.id.in_(ids or {-1}))
        us = list((await a.execute(q)).scalars())
        gs = list((await a.execute(select(Grant.user_id, Grant.role).where(Grant.user_id.in_([u.id for u in us] or [-1])))).all())
    roles: dict[int, set[str]] = {}
    for uid, r in gs:
        roles.setdefault(uid, set()).add(r)
    return {u.id: {"id": u.id, "ho_ten": u.ho_ten, "chuc_danh": u.chuc_danh, "don_vi": u.don_vi, "username": u.username,
                   "hoat_dong": u.trang_thai == "hoat_dong" and "man_hinh_tv" not in roles.get(u.id, set())} for u in us}


async def _me_name(user: CurrentUser) -> str:
    async with admin_sessionmaker()() as a:
        u = await a.get(User, user.id)
    return u.ho_ten if u else user.username


async def _conv(s: AsyncSession, hid: int, user: CurrentUser) -> tuple[HoiThoai, ThanhVien]:
    h = await s.get(HoiThoai, hid)
    tv = (await s.execute(select(ThanhVien).where(ThanhVien.hoi_thoai_id == hid, ThanhVien.user_id == user.id))).scalar() if h else None
    if h is None or tv is None or h.tenant_id != s.info["tenant_id"]:
        raise HTTPException(404, "Không tìm thấy cuộc trao đổi")
    return h, tv


@router.get("/nguoi-nhan")
async def directory(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    _check(user)
    ppl = await _people(s.info["tenant_id"])
    return {"nguoi": sorted([p for p in ppl.values() if p["hoat_dong"] and p["id"] != user.id], key=lambda p: p["ho_ten"]),
            "phat_hanh_cong_van": can_issue(user)}


async def _link(s: AsyncSession, user: CurrentUser, loai: str | None, lid: int | None) -> dict:
    if not loai:
        return {}
    tid = s.info["tenant_id"]
    if loai == "canh_bao":
        from app.alerts.models import Alert

        a = await s.get(Alert, lid or 0)
        if a is None or a.tenant_id != tid or not user.can("doc", a.nhom):
            raise HTTPException(404, "Không tìm thấy cảnh báo")
        return {"lien_ket_ten": a.tieu_de[:500], "lien_ket_url": f"/canh-bao?id={a.id}"}
    if loai == "phan_anh":
        from app.field_reports.models import FieldReport

        r = await s.get(FieldReport, lid or 0)
        if r is None or r.tenant_id != tid or not user.can("doc", "tthc_pakn"):
            raise HTTPException(404, "Không tìm thấy phản ánh")
        return {"lien_ket_ten": f"{r.ma} – {r.tieu_de}"[:500], "lien_ket_url": f"/phan-anh?id={r.id}"}
    raise HTTPException(422, "Loại liên kết không hợp lệ")


def _title(h: HoiThoai, members: list[int], ppl: dict[int, dict], me: int) -> str:
    if h.tieu_de:
        return h.tieu_de
    others = [ppl[m]["ho_ten"] for m in members if m != me and m in ppl]
    return ", ".join(others[:3]) + (f" và {len(others) - 3} người" if len(others) > 3 else "") or "Trao đổi"


@router.get("/hoi-thoai")
async def conversations(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> list:
    _check(user)
    mine = {t.hoi_thoai_id: t for t in (await s.execute(select(ThanhVien).where(ThanhVien.user_id == user.id))).scalars()}
    if not mine:
        return []
    hs = list((await s.execute(select(HoiThoai).where(HoiThoai.id.in_(mine)).order_by(HoiThoai.cap_nhat_luc.desc()))).scalars())
    members: dict[int, list[int]] = {}
    for hid, uid in (await s.execute(select(ThanhVien.hoi_thoai_id, ThanhVien.user_id).where(ThanhVien.hoi_thoai_id.in_(mine)))).all():
        members.setdefault(hid, []).append(uid)
    last = {}
    sub = select(TinNhan.hoi_thoai_id, func.max(TinNhan.id).label("m")).where(TinNhan.hoi_thoai_id.in_(mine)).group_by(TinNhan.hoi_thoai_id).subquery()
    for t in (await s.execute(select(TinNhan).join(sub, TinNhan.id == sub.c.m))).scalars():
        last[t.hoi_thoai_id] = t
    unread = dict((await s.execute(select(TinNhan.hoi_thoai_id, func.count(TinNhan.id)).join(
        ThanhVien, (ThanhVien.hoi_thoai_id == TinNhan.hoi_thoai_id) & (ThanhVien.user_id == user.id))
        .where(TinNhan.id > ThanhVien.doc_den, TinNhan.nguoi_gui_id != user.id).group_by(TinNhan.hoi_thoai_id))).all())
    ppl = await _people(s.info["tenant_id"], {u for v in members.values() for u in v} | {t.nguoi_gui_id for t in last.values()})
    out = []
    for h in hs:
        t = last.get(h.id)
        prev = None
        if t:
            who = "Bạn" if t.nguoi_gui_id == user.id else ppl.get(t.nguoi_gui_id, {}).get("ho_ten", "")
            body = "Đã gửi công văn" if t.van_ban_id and not t.noi_dung else (t.noi_dung or "Đã gửi tệp")
            prev = {"nguoi": who, "noi_dung": body[:120], "luc": t.gui_luc, "he_thong": t.he_thong}
        out.append({"id": h.id, "tieu_de": _title(h, members.get(h.id, []), ppl, user.id), "loai": h.loai, "lien_ket_loai": h.lien_ket_loai,
                    "lien_ket_ten": h.lien_ket_ten, "lien_ket_url": h.lien_ket_url, "so_thanh_vien": len(members.get(h.id, [])),
                    "chua_doc": unread.get(h.id, 0), "cuoi": prev, "cap_nhat_luc": h.cap_nhat_luc, "is_sample": h.is_sample})
    return jsonable(out)


@router.get("/chua-doc")
async def unread_total(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    if "man_hinh_tv" in user.roles:
        return {"tong": 0}
    n = (await s.execute(select(func.count(TinNhan.id)).join(
        ThanhVien, (ThanhVien.hoi_thoai_id == TinNhan.hoi_thoai_id) & (ThanhVien.user_id == user.id))
        .where(TinNhan.id > ThanhVien.doc_den, TinNhan.nguoi_gui_id != user.id))).scalar()
    return {"tong": int(n or 0)}


class CongVanIn(BaseModel):
    so_ky_hieu: str = Field(min_length=1, max_length=100)
    trich_yeu: str = Field(min_length=1)
    loai: str = Field("cong_van", pattern="^(cong_van|thong_bao|chi_thi|quyet_dinh|ke_hoach)$")
    han_thuc_hien: date | None = None


class TinIn(BaseModel):
    noi_dung: str = Field("", max_length=4000)
    tep_keys: list[str] = []
    cong_van: CongVanIn | None = None


class HoiThoaiIn(BaseModel):
    thanh_vien_ids: list[int] = Field(min_length=1, max_length=50)
    tieu_de: str = Field("", max_length=300)
    lien_ket_loai: str | None = None
    lien_ket_id: int | None = None
    tin_dau: TinIn | None = None


async def _check_members(tid: int, ids: list[int], me: int) -> dict[int, dict]:
    ppl = await _people(tid, set(ids))
    bad = [i for i in ids if i not in ppl or not ppl[i]["hoat_dong"]]
    if bad or me in ids and len(ids) == 1:
        raise HTTPException(422, "Người nhận không hợp lệ (phải là cán bộ đang hoạt động của đơn vị)")
    return ppl


@router.post("/hoi-thoai", status_code=201)
async def create(body: HoiThoaiIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    _check(user)
    tid = s.info["tenant_id"]
    ids = sorted({i for i in body.thanh_vien_ids if i != user.id})
    await _check_members(tid, ids, user.id)
    link = await _link(s, user, body.lien_ket_loai, body.lien_ket_id)
    direct = len(ids) == 1 and not body.tieu_de.strip() and not link
    if direct:  # trao đổi trực tiếp hai người: dùng lại cuộc đã có
        cands = select(ThanhVien.hoi_thoai_id).where(ThanhVien.user_id == user.id)
        for h in (await s.execute(select(HoiThoai).where(HoiThoai.loai == "truc_tiep", HoiThoai.id.in_(cands)))).scalars():
            mem = set((await s.execute(select(ThanhVien.user_id).where(ThanhVien.hoi_thoai_id == h.id))).scalars())
            if mem == {user.id, ids[0]}:
                if body.tin_dau:
                    await _send(s, h, user, body.tin_dau)
                return {"id": h.id, "da_co": True}
    h = HoiThoai(tenant_id=tid, tieu_de=body.tieu_de.strip() or (link.get("lien_ket_ten") or ""), loai="truc_tiep" if direct else ("viec" if link else "nhom"),
                 lien_ket_loai=body.lien_ket_loai if link else None, lien_ket_id=body.lien_ket_id if link else None, tao_boi=user.id, **link)
    s.add(h)
    await s.flush()
    for uid in [user.id, *ids]:
        s.add(ThanhVien(tenant_id=tid, hoi_thoai_id=h.id, user_id=uid))
    await s.flush()
    if body.tin_dau:
        await _send(s, h, user, body.tin_dau)
    else:
        await s.commit()
    await record_change(user, tid, f"tin_nhan:hoi_thoai:{h.id}:tao", None, {"thanh_vien": [user.id, *ids], "lien_ket": link.get("lien_ket_url")})
    return {"id": h.id, "da_co": False}


def _file_out(f: TepTinNhan) -> dict:
    return {"key": f.key, "ten": f.ten, "content_type": f.content_type, "kich_thuoc": f.kich_thuoc}


@router.get("/hoi-thoai/{hid}")
async def thread(hid: int, truoc: int | None = None, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    _check(user)
    h, me = await _conv(s, hid, user)
    q = select(TinNhan).where(TinNhan.hoi_thoai_id == hid)
    if truoc:
        q = q.where(TinNhan.id < truoc)
    msgs = list(reversed(list((await s.execute(q.order_by(TinNhan.id.desc()).limit(60))).scalars())))
    files: dict[int, list] = {}
    for f in (await s.execute(select(TepTinNhan).where(TepTinNhan.tin_nhan_id.in_([m.id for m in msgs] or [-1])))).scalars():
        files.setdefault(f.tin_nhan_id, []).append(_file_out(f))
    vbs = {}
    vb_ids = [m.van_ban_id for m in msgs if m.van_ban_id]
    if vb_ids:
        from app.van_ban.models import VanBan

        for v in (await s.execute(select(VanBan).where(VanBan.id.in_(vb_ids)))).scalars():
            vbs[v.id] = {"id": v.id, "so_ky_hieu": v.so_ky_hieu, "trich_yeu": v.trich_yeu, "loai": v.loai, "ngay_ban_hanh": v.ngay_ban_hanh,
                         "han_thuc_hien": v.han_thuc_hien, "co_quan_ban_hanh": v.co_quan_ban_hanh, "nguoi_ky": v.nguoi_ky, "file_key": v.file_key}
    member_ids = list((await s.execute(select(ThanhVien.user_id).where(ThanhVien.hoi_thoai_id == hid))).scalars())
    ppl = await _people(s.info["tenant_id"], set(member_ids) | {m.nguoi_gui_id for m in msgs})
    if msgs and not truoc and msgs[-1].id > me.doc_den:
        me.doc_den = msgs[-1].id
        from app.noti.service import mark_read_key

        await mark_read_key(s, user.id, f"tin:{hid}")
        await s.commit()
    return jsonable({
        "id": h.id, "tieu_de": _title(h, member_ids, ppl, user.id), "loai": h.loai, "lien_ket_loai": h.lien_ket_loai, "lien_ket_ten": h.lien_ket_ten,
        "lien_ket_url": h.lien_ket_url, "thanh_vien": [ppl[i] for i in member_ids if i in ppl], "phat_hanh_cong_van": can_issue(user),
        "tin": [{"id": m.id, "nguoi_gui": ppl.get(m.nguoi_gui_id, {"id": m.nguoi_gui_id, "ho_ten": "?"}), "cua_toi": m.nguoi_gui_id == user.id,
                 "noi_dung": m.noi_dung, "gui_luc": m.gui_luc, "he_thong": m.he_thong, "tep": files.get(m.id, []), "cong_van": vbs.get(m.van_ban_id)}
                for m in msgs],
        "con_nua": len(msgs) == 60,
    })


async def _send(s: AsyncSession, h: HoiThoai, user: CurrentUser, body: TinIn) -> TinNhan:
    tid = s.info["tenant_id"]
    keys = list(dict.fromkeys(body.tep_keys))
    if not body.noi_dung.strip() and not keys and not body.cong_van:
        raise HTTPException(422, "Tin nhắn trống")
    if len(keys) > TOI_DA_TEP:
        raise HTTPException(422, f"Tối đa {TOI_DA_TEP} tệp mỗi tin")
    sf = {f.key: f for f in (await s.execute(select(StoredFile).where(StoredFile.key.in_(keys or ["-"])))).scalars()}
    if any(k not in sf or sf[k].nguoi_tai_len_id != user.id for k in keys):
        raise HTTPException(422, "Tệp không hợp lệ (tải lên lại rồi gửi)")
    vb_id = None
    if body.cong_van:
        if not can_issue(user):
            raise HTTPException(403, "Chỉ lãnh đạo, quản trị đơn vị phát hành công văn")
        from app.platform.models import Tenant
        from app.van_ban.models import VanBan

        doc = next((sf[k] for k in keys if sf[k].content_type in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")), None)
        if doc is None:
            raise HTTPException(422, "Công văn cần kèm tệp PDF hoặc Word")
        t = await s.get(Tenant, tid)
        nv: list[int] = []
        if h.lien_ket_loai == "canh_bao" and h.lien_ket_id:
            from app.alerts.models import FollowUpCase

            c = (await s.execute(select(FollowUpCase.id).where(FollowUpCase.alert_id == h.lien_ket_id))).scalar()
            nv = [c] if c else []
        vb = VanBan(tenant_id=tid, so_ky_hieu=body.cong_van.so_ky_hieu.strip(), ngay_ban_hanh=date.today(), loai=body.cong_van.loai,
                    co_quan_ban_hanh=f"UBND {t.ten[0].lower() + t.ten[1:]}" if t else "UBND", nguoi_ky=await _me_name(user),
                    trich_yeu=body.cong_van.trich_yeu.strip(), file_key=doc.key, lien_ket=h.lien_ket_url, han_thuc_hien=body.cong_van.han_thuc_hien,
                    trang_thai="con_hieu_luc", nhiem_vu_ids=nv)
        s.add(vb)
        await s.flush()
        vb_id = vb.id
    m = TinNhan(tenant_id=tid, hoi_thoai_id=h.id, nguoi_gui_id=user.id, noi_dung=body.noi_dung.strip(), van_ban_id=vb_id)
    s.add(m)
    await s.flush()
    for k in keys:
        f = sf[k]
        s.add(TepTinNhan(tenant_id=tid, tin_nhan_id=m.id, hoi_thoai_id=h.id, key=k, ten=f.ten_goc, content_type=f.content_type, kich_thuoc=f.kich_thuoc))
    h.cap_nhat_luc = datetime.now(UTC)
    me = (await s.execute(select(ThanhVien).where(ThanhVien.hoi_thoai_id == h.id, ThanhVien.user_id == user.id))).scalar()
    if me:
        me.doc_den = m.id
    await s.commit()
    if vb_id:
        await record_change(user, tid, f"van_ban:{vb_id}:phat_hanh_qua_tin_nhan", None,
                            {"hoi_thoai": h.id, "so_ky_hieu": body.cong_van.so_ky_hieu, "lien_ket": h.lien_ket_url})
    from app.noti.service import notify

    others = list((await s.execute(select(ThanhVien.user_id).where(ThanhVien.hoi_thoai_id == h.id, ThanhVien.user_id != user.id))).scalars())
    name = await _me_name(user)
    where = f" · {h.tieu_de}" if h.tieu_de else ""
    preview = body.noi_dung.strip() or (f"Đã gửi {len(keys)} tệp" if keys else "")
    if body.cong_van:
        han = f" Hạn xử lý {body.cong_van.han_thuc_hien.strftime('%d/%m/%Y')}." if body.cong_van.han_thuc_hien else ""
        await notify(s, tid, others, "cong_van", f"{name} gửi công văn số {body.cong_van.so_ky_hieu}", f"{body.cong_van.trich_yeu}.{han}",
                     f"/tin-nhan?id={h.id}", "khan" if h.lien_ket_loai == "canh_bao" else "quan_trong")
    if preview:
        await notify(s, tid, others, "tin_nhan", f"{name}{where}", preview[:200], f"/tin-nhan?id={h.id}", "thuong", f"tin:{h.id}")
    return m


@router.post("/hoi-thoai/{hid}/tin", status_code=201)
async def send(hid: int, body: TinIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    _check(user)
    h, _ = await _conv(s, hid, user)
    m = await _send(s, h, user, body)
    return {"id": m.id, "van_ban_id": m.van_ban_id}


class ThemIn(BaseModel):
    user_ids: list[int] = Field(min_length=1, max_length=50)


@router.post("/hoi-thoai/{hid}/thanh-vien")
async def add_members(hid: int, body: ThemIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    _check(user)
    h, _ = await _conv(s, hid, user)
    if h.loai == "truc_tiep":
        raise HTTPException(409, "Trao đổi trực tiếp hai người — tạo nhóm mới để thêm người")
    tid = s.info["tenant_id"]
    have = set((await s.execute(select(ThanhVien.user_id).where(ThanhVien.hoi_thoai_id == hid))).scalars())
    new = [i for i in dict.fromkeys(body.user_ids) if i not in have]
    if not new:
        return {"them": 0}
    ppl = await _check_members(tid, new, user.id)
    for i in new:
        s.add(ThanhVien(tenant_id=tid, hoi_thoai_id=hid, user_id=i))
    s.add(TinNhan(tenant_id=tid, hoi_thoai_id=hid, nguoi_gui_id=user.id, he_thong=True,
                  noi_dung=f"{await _me_name(user)} đã thêm {', '.join(ppl[i]['ho_ten'] for i in new)}"))
    h.cap_nhat_luc = datetime.now(UTC)
    await s.commit()
    from app.noti.service import notify

    await notify(s, tid, new, "tin_nhan", f"{await _me_name(user)} đã thêm bạn vào trao đổi", h.tieu_de or "", f"/tin-nhan?id={hid}", "thuong", f"tin:{hid}")
    return {"them": len(new)}


@router.post("/tep", status_code=201)
async def upload(file: UploadFile = File(...), s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    """Tải tệp để gửi kèm tin nhắn (ảnh, PDF, Word, Excel ≤ 10 MB) — mọi cán bộ nhắn tin được."""
    _check(user)
    content = await file.read(storage.MAX_BYTES + 1)
    if len(content) > storage.MAX_BYTES:
        raise HTTPException(422, "Tệp vượt quá 10 MB")
    ctype = storage.sniff(content)
    if ctype is None:
        raise HTTPException(422, "Chỉ gửi được ảnh JPG/PNG/WEBP, PDF, Word, Excel")
    tid = s.info["tenant_id"]
    key = storage.save(tid, content, ctype)
    s.add(StoredFile(tenant_id=tid, key=key, ten_goc=(file.filename or "tep")[:300], content_type=ctype, kich_thuoc=len(content), nguoi_tai_len_id=user.id))
    await s.commit()
    return {"key": key, "ten": file.filename, "content_type": ctype, "kich_thuoc": len(content)}


@router.get("/tep/{key}")
async def download(key: str, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> Response:
    _check(user)
    f = (await s.execute(select(TepTinNhan).where(TepTinNhan.key == key))).scalars().first()
    if f is None:
        raise HTTPException(404, "Không tìm thấy tệp")
    await _conv(s, f.hoi_thoai_id, user)
    from urllib.parse import quote

    return Response(storage.load(f.tenant_id, f.key, f.content_type), media_type=f.content_type,
                    headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(f.ten)}", "X-Content-Type-Options": "nosniff", "Cache-Control": "private"})


async def may_read_file(s: AsyncSession, key: str, user: CurrentUser) -> bool:
    """Dùng cho /api/files: tệp đính kèm tin nhắn chỉ thành viên đọc được (trừ khi là tệp công văn đã vào sổ văn bản)."""
    hids = set((await s.execute(select(TepTinNhan.hoi_thoai_id).where(TepTinNhan.key == key))).scalars())
    if not hids:
        return True
    from app.van_ban.models import VanBan

    if (await s.execute(select(VanBan.id).where(VanBan.file_key == key))).first():
        return True
    return bool((await s.execute(select(ThanhVien.id).where(ThanhVien.hoi_thoai_id.in_(hids), ThanhVien.user_id == user.id))).first())
