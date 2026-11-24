"""Quản lý dữ liệu tập trung: xem, tìm, thêm, sửa, xóa mọi bộ dữ liệu của đơn vị theo quyền từng nhóm dữ liệu.

- Đọc: quyền `doc` nhóm dữ liệu; thêm/sửa: `nhap` hoặc `duyet`; xóa: `duyet` (danh mục: `duyet` quản trị).
- Sửa bản ghi đã xác nhận/đối soát → quay về trạng thái chờ, phải xác nhận lại; bắt buộc ghi lý do (DT V.3: không sửa ngầm).
- Xóa luôn phải ghi lý do; mọi thay đổi ghi nhật ký (trước/sau)."""
import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, tenant_db
from app.core.periods import KyError, parse_ky
from app.core.principal import CurrentUser
from app.data_admin.registry import BY_KEY, DATASETS, Dataset, F

router = APIRouter(prefix="/api/du-lieu", tags=["quan-ly-du-lieu"])
NGHIEP_VU = ["ktxh", "dan_cu", "ngan_sach", "dau_tu_cong", "cong_trinh", "tthc_pakn", "gd_yt_mt"]


# ---------------- quyền ----------------
def _groups(ds: Dataset) -> list[str]:
    return NGHIEP_VU if ds.nhom == "@indicator" else ds.nhom.split("|")


def can(user: CurrentUser, ds: Dataset, act: str, nhom: str | None = None) -> bool:
    """act: doc | sua | xoa. `nhom` = nhóm của bản ghi cụ thể (bộ dữ liệu theo chỉ tiêu)."""
    if "man_hinh_tv" in user.roles:
        return False
    groups = [nhom] if nhom else _groups(ds)
    if ds.nhom == "quan_tri" or "|" in ds.nhom:
        need = {"doc": ("doc",), "sua": ("duyet",), "xoa": ("duyet",)}[act]
    else:
        need = {"doc": ("doc",), "sua": ("nhap", "duyet"), "xoa": ("duyet",)}[act]
    return any(user.can(q, g) for g in groups for q in need)


def _ds(key: str, user: CurrentUser, act: str = "doc") -> Dataset:
    ds = BY_KEY.get(key)
    if ds is None:
        raise HTTPException(404, "Không có bộ dữ liệu này")
    if not can(user, ds, act):
        raise HTTPException(403, "Bạn không có quyền với bộ dữ liệu này")
    return ds


async def _ind_groups(s: AsyncSession, tid: int) -> dict[int, str]:
    from app.catalog.models import Indicator

    return {i: n for i, n in (await s.execute(select(Indicator.id, Indicator.nhom).where(Indicator.tenant_id == tid))).all()}


# ---------------- giá trị ----------------
def _out_val(f: F, v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return format(v.normalize(), "f")
    if isinstance(v, datetime | date):
        return v.isoformat()
    if f.kind == "enum" and f.name == "lop":
        return str(v)
    return v


def _parse(f: F, raw: Any, cats: dict[str, set[str]], refs: dict[str, set[int]]) -> Any:
    if f.kind in ("multi", "refmulti") and raw is None:
        return []
    if raw is None or (isinstance(raw, str) and raw.strip() == "" and f.kind not in ("text", "textarea", "enum", "multi", "refmulti")):
        if f.required:
            raise HTTPException(422, f"Thiếu {f.label}")
        return None
    try:
        if f.kind in ("text", "textarea"):
            v = str(raw).strip()
            if f.required and not v:
                raise HTTPException(422, f"Thiếu {f.label}")
            if f.name == "lien_ket" and v and not (v.startswith("https://") or v.startswith("/")):
                raise HTTPException(422, "Liên kết phải bắt đầu bằng https:// hoặc / (trang trong hệ thống)")
            return v or (None if f.name == "lien_ket" else v)
        if f.kind == "time":
            v = str(raw).strip()[:5]
            if not (len(v) == 5 and v[2] == ":" and v[:2].isdigit() and v[3:].isdigit() and int(v[:2]) < 24 and int(v[3:]) < 60):
                raise HTTPException(422, f"{f.label}: giờ theo dạng HH:MM")
            return v
        if f.kind == "file":
            v = str(raw).strip()
            if v not in refs.get("__file__", set()):
                raise HTTPException(422, f"{f.label}: tệp không tồn tại")
            return v
        if f.kind == "refmulti":
            vals = list(dict.fromkeys(int(x) for x in (raw if isinstance(raw, list) else [])))
            if set(vals) - refs.get(f.ref or "", set()):
                raise HTTPException(422, f"{f.label}: không tìm thấy")
            return vals
        if f.kind == "int":
            return int(raw)
        if f.kind == "dec":
            return Decimal(str(raw).replace(" ", "").replace(",", "."))
        if f.kind == "bool":
            return raw if isinstance(raw, bool) else str(raw).lower() in ("1", "true", "co", "có", "x")
        if f.kind == "date":
            return date.fromisoformat(str(raw)[:10])
        if f.kind == "datetime":
            d = datetime.fromisoformat(str(raw))
            return d if d.tzinfo else d.replace(tzinfo=UTC)
        if f.kind == "ky":
            parse_ky(str(raw).strip())
            return str(raw).strip()
        if f.kind == "multi":
            vals = list(dict.fromkeys(raw if isinstance(raw, list) else [x for x in str(raw).split(",") if x]))
            if set(vals) - set(f.options or {}):
                raise HTTPException(422, f"{f.label}: giá trị không hợp lệ")
            return vals
        if f.kind == "enum":
            v = str(raw)
            if v not in (f.options or {}):
                if v == "" and not f.required:
                    return None if f.name not in ("gioi",) else ""
                raise HTTPException(422, f"{f.label}: giá trị không hợp lệ")
            return int(v) if f.name == "lop" else v
        if f.kind == "cat":
            v = str(raw).strip()
            if v not in cats.get(f.cat or "", set()):
                raise HTTPException(422, f"{f.label}: không có trong danh mục")
            return v
        if f.kind == "ref":
            v = int(raw)
            if v not in refs.get(f.ref or "", set()):
                raise HTTPException(422, f"{f.label}: không tìm thấy")
            return v
    except HTTPException:
        raise
    except (ValueError, InvalidOperation, KyError, TypeError) as e:
        raise HTTPException(422, f"{f.label}: định dạng không hợp lệ") from e
    return raw


async def _options(s: AsyncSession, tid: int, ds: Dataset) -> tuple[dict[str, list], dict[str, dict]]:
    """Lựa chọn cho trường danh mục dùng chung và trường tham chiếu (chỉ tiêu, địa bàn, dự án, công trình của đơn vị)."""
    from app.catalog.models import Indicator
    from app.platform.models import ResidentialGroup, SharedCatalog
    from app.projects.models import Project
    from app.works.models import Work

    cats: dict[str, list] = {}
    for f in ds.fields:
        if f.kind == "cat" and f.cat and f.cat not in cats:
            cats[f.cat] = [{"value": m, "label": f"{m} – {t}"} for m, t in (await s.execute(
                select(SharedCatalog.ma, SharedCatalog.ten).where(SharedCatalog.loai == f.cat).order_by(SharedCatalog.ma))).all()]
    refs: dict[str, dict] = {}
    for f in ds.fields:
        if f.kind not in ("ref", "refmulti") or f.ref in refs:
            continue
        if f.ref == "case":
            from app.alerts.models import Alert, FollowUpCase

            rows = (await s.execute(select(FollowUpCase.id, Alert.tieu_de, FollowUpCase.co_quan_xu_ly).join(Alert, Alert.id == FollowUpCase.alert_id)
                                    .where(FollowUpCase.tenant_id == tid).order_by(FollowUpCase.id.desc()))).all()
            refs["case"] = {i: f"{t} – {c}" for i, t, c in rows}
            continue
        if f.ref == "indicator":
            rows = (await s.execute(select(Indicator.id, Indicator.ma_chi_tieu, Indicator.ten).where(Indicator.tenant_id == tid).order_by(Indicator.ma_chi_tieu))).all()
            refs["indicator"] = {i: f"{m} – {t}" for i, m, t in rows}
        elif f.ref == "tdp":
            rows = (await s.execute(select(ResidentialGroup.id, ResidentialGroup.ten).where(ResidentialGroup.tenant_id == tid).order_by(ResidentialGroup.ma_tdp))).all()
            refs["tdp"] = {i: t for i, t in rows}
        elif f.ref == "project":
            rows = (await s.execute(select(Project.id, Project.ma_du_an, Project.ten).where(Project.tenant_id == tid).order_by(Project.ma_du_an))).all()
            refs["project"] = {i: f"{m} – {t}" for i, m, t in rows}
        elif f.ref == "work":
            rows = (await s.execute(select(Work.id, Work.ma_cong_trinh, Work.ten).where(Work.tenant_id == tid).order_by(Work.ma_cong_trinh))).all()
            refs["work"] = {i: f"{m} – {t}" for i, m, t in rows}
    return cats, refs


NHOM_TEN = {"ktxh": "kinh tế – xã hội", "dan_cu": "dân cư", "ngan_sach": "ngân sách", "dau_tu_cong": "đầu tư công", "cong_trinh": "công trình",
            "tthc_pakn": "dịch vụ công – phản ánh", "gd_yt_mt": "giáo dục – y tế – môi trường"}


def quyen_mo_ta(ds: Dataset) -> str:
    """Ai được thêm/sửa/xóa bộ dữ liệu — hiện cho người dùng khi họ chỉ có quyền xem."""
    if ds.nhom == "quan_tri":
        return "Thêm, sửa, xóa: quản trị đơn vị."
    if "|" in ds.nhom:
        return "Thêm, sửa, xóa: lãnh đạo và quản trị đơn vị."
    nhom = "nhóm của chỉ tiêu" if ds.nhom == "@indicator" else f"nhóm {NHOM_TEN.get(ds.nhom, ds.nhom)}"
    them = "" if ds.them else " Thêm mới tại màn hình nghiệp vụ."
    return (f"Thêm, sửa: cán bộ nhập liệu, cán bộ xác nhận, cơ quan chuyên ngành được giao {nhom}. "
            f"Xóa: cán bộ xác nhận, cơ quan chuyên ngành.{them} Lãnh đạo xem và chỉ đạo, không nhập số.")


def _schema(ds: Dataset, user: CurrentUser) -> dict:
    return {"quyen_mo_ta": quyen_mo_ta(ds), "them_link": ds.them_link if can(user, ds, "sua") else None,"key": ds.key, "ten": ds.ten, "nhom_phan_he": ds.nhom_phan_he, "mo_ta": ds.mo_ta, "link": ds.link, "co_minh_hoa": ds.sample,
            "them": ds.them and can(user, ds, "sua"), "sua": can(user, ds, "sua"), "xoa": can(user, ds, "xoa"),
            "xac_nhan": {"truong": ds.confirm.field, "khoa": list(ds.confirm.locked), "ve": ds.confirm.reset_to} if ds.confirm else None,
            "truong": [{"name": f.name, "label": f.label, "kind": f.kind, "required": f.required, "options": f.options, "cat": f.cat, "ref": f.ref,
                        "readonly": f.readonly, "create_only": f.create_only, "list": f.list, "help": f.help} for f in ds.fields]}


def _row(ds: Dataset, r: Any, refs: dict[str, dict]) -> dict:
    out: dict[str, Any] = {"id": r.id}
    for f in ds.fields:
        v = getattr(r, f.name)
        out[f.name] = _out_val(f, v)
        if f.kind == "ref":
            out[f"{f.name}__nhan"] = refs.get(f.ref or "", {}).get(v) if v is not None else None
    if ds.sample:
        out["is_sample"] = bool(getattr(r, "is_sample", False))
    return out


def _snap(ds: Dataset, r: Any) -> dict:
    return {f.name: _out_val(f, getattr(r, f.name)) for f in ds.fields}


# ---------------- API ----------------
@router.get("")
async def catalog(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    """Các bộ dữ liệu người dùng được xem, kèm số bản ghi."""
    tid = s.info["tenant_id"]
    out = []
    groups = await _ind_groups(s, tid)
    readable = {g for g in NGHIEP_VU if user.can("doc", g)}
    for ds in DATASETS:
        if not can(user, ds, "doc"):
            continue
        m = ds.model
        q = select(func.count(m.id)).where(m.tenant_id == tid)
        if ds.nhom == "@indicator":
            q = q.where(m.indicator_id.in_([i for i, g in groups.items() if g in readable] or [-1]))
        n = int((await s.execute(q)).scalar() or 0)
        mau = int((await s.execute(q.where(m.is_sample.is_(True)))).scalar() or 0) if ds.sample else 0
        out.append({**_schema(ds, user), "so_ban_ghi": n, "so_minh_hoa": mau})
    return {"bo_du_lieu": out}


@router.get("/{key}")
async def rows(key: str, request: Request, q: str = "", page: int = 1, size: int = 50, minh_hoa: str = "",
               s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    ds = _ds(key, user)
    tid = s.info["tenant_id"]
    m = ds.model
    stmt = select(m).where(m.tenant_id == tid)
    if ds.nhom == "@indicator":
        groups = await _ind_groups(s, tid)
        stmt = stmt.where(m.indicator_id.in_([i for i, g in groups.items() if user.can("doc", g)] or [-1]))
    if q.strip() and ds.search:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(*[func.lower(cast(getattr(m, c), String)).like(like) for c in ds.search]))
    for f in ds.fields:  # bộ lọc chính xác ?loc_<trường>=giá trị
        v = request.query_params.get(f"loc_{f.name}")
        if v not in (None, ""):
            stmt = stmt.where(getattr(m, f.name) == (int(v) if f.kind in ("ref", "int") or f.name == "lop" else v))
    if ds.sample and minh_hoa in ("co", "khong"):
        stmt = stmt.where(m.is_sample.is_(minh_hoa == "co"))
    total = int((await s.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0)
    size = max(1, min(size, 200))
    page = max(1, page)
    data = list((await s.execute(stmt.order_by(*[getattr(m, c) for c in ds.order], m.id).offset((page - 1) * size).limit(size))).scalars())
    cats, refs = await _options(s, tid, ds)
    return {"schema": _schema(ds, user), "rows": [_row(ds, r, refs) for r in data], "tong": total, "trang": page, "co_trang": size,
            "lua_chon": {"cat": cats, "ref": {k: [{"value": i, "label": t} for i, t in v.items()] for k, v in refs.items()}}}


class RowIn(BaseModel):
    data: dict[str, Any]
    ly_do: str = ""


async def _values(s: AsyncSession, tid: int, ds: Dataset, data: dict, creating: bool) -> dict[str, Any]:
    cats_l, refs_l = await _options(s, tid, ds)
    cats = {k: {o["value"] for o in v} for k, v in cats_l.items()}
    refs = {k: set(v) for k, v in refs_l.items()}
    if any(f.kind == "file" for f in ds.fields):
        from app.files.models import StoredFile

        keys = [str(data[f.name]) for f in ds.fields if f.kind == "file" and data.get(f.name)]
        refs["__file__"] = set((await s.execute(select(StoredFile.key).where(StoredFile.key.in_(keys or ["-"])))).scalars())
    out: dict[str, Any] = {}
    for f in ds.fields:
        if f.readonly or (f.create_only and not creating):
            continue
        if f.name in data:
            out[f.name] = _parse(f, data[f.name], cats, refs)
            col = ds.model.__table__.c.get(f.name)
            maxlen = getattr(getattr(col, "type", None), "length", None)
            if maxlen and isinstance(out[f.name], str) and len(out[f.name]) > maxlen:
                raise HTTPException(422, f"{f.label}: tối đa {maxlen} ký tự")
        elif creating and f.required:
            raise HTTPException(422, f"Thiếu {f.label}")
    if "nam" in out and "ky" in out and parse_ky(out["ky"]).nam != out["nam"]:
        raise HTTPException(422, "Kỳ không thuộc năm đã chọn")
    for a, b in (("giai_quyet", "tiep_nhan"), ("dung_han", "giai_quyet"), ("truc_tuyen", "tiep_nhan")):
        if a in out and b in out and out[a] is not None and out[b] is not None and out[a] > out[b]:
            raise HTTPException(422, f"{a.replace('_', ' ').capitalize()} không được lớn hơn {b.replace('_', ' ')}")
    if out.get("danh_gia_hai_long") is not None and not 1 <= out["danh_gia_hai_long"] <= 5:
        raise HTTPException(422, "Mức hài lòng từ 1 đến 5")
    for k in ("lat",):
        if out.get(k) is not None and not (Decimal(8) <= out[k] <= Decimal(24)):
            raise HTTPException(422, "Vĩ độ phải nằm trong lãnh thổ Việt Nam")
    if out.get("lng") is not None and not (Decimal(102) <= out["lng"] <= Decimal(110)):
        raise HTTPException(422, "Kinh độ phải nằm trong lãnh thổ Việt Nam")
    return out


def _check_row_perm(user: CurrentUser, ds: Dataset, act: str, nhom: str | None) -> None:
    if not can(user, ds, act, nhom):
        raise HTTPException(403, "Bạn không có quyền với bản ghi thuộc nhóm dữ liệu này")


async def _commit(s: AsyncSession) -> None:
    try:
        await s.commit()
    except IntegrityError as e:
        await s.rollback()
        raise HTTPException(409, "Trùng mã hoặc bản ghi đang được dữ liệu khác tham chiếu") from e


@router.post("/{key}", status_code=201)
async def create(key: str, body: RowIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    ds = _ds(key, user, "sua")
    if not ds.them:
        raise HTTPException(409, "Bộ dữ liệu này thêm mới tại màn hình nghiệp vụ")
    tid = s.info["tenant_id"]
    vals = await _values(s, tid, ds, body.data, creating=True)
    if ds.nhom == "@indicator":
        _check_row_perm(user, ds, "sua", (await _ind_groups(s, tid)).get(vals["indicator_id"]))
    m = ds.model
    r = m(tenant_id=tid, **{**ds.defaults, **vals})
    if ds.sample:
        r.is_sample = False
    if ds.confirm:
        setattr(r, ds.confirm.field, ds.confirm.reset_to)
    if hasattr(r, "nguoi_nhap_id"):
        r.nguoi_nhap_id = user.id
    if hasattr(r, "nguoi_tao_id"):
        r.nguoi_tao_id = user.id
    if ds.key == "so_lieu":
        r.thoi_diem_dong_bo = datetime.now(UTC)
    s.add(r)
    await _commit(s)
    await record_change(user, tid, f"du_lieu:{ds.key}:{r.id}:tao", None, _snap(ds, r))
    if ds.key == "thong_bao" and r.tu_ngay <= date.today():
        from app.auth.models import Grant
        from app.core.db import admin_sessionmaker
        from app.noti.service import notify

        async with admin_sessionmaker()() as a:
            q = select(Grant.user_id).where(Grant.tenant_id == tid, Grant.role != "man_hinh_tv")
            if r.doi_tuong:
                q = q.where(Grant.role.in_(r.doi_tuong))
            ids = set((await a.execute(q)).scalars())
        await notify(s, tid, ids, "thong_bao", r.tieu_de, r.noi_dung or "", r.lien_ket or "/", r.muc_do, f"thong_bao:{r.id}", bo_qua=user.id)
    _, refs = await _options(s, tid, ds)
    return _row(ds, r, refs)


async def _get(s: AsyncSession, ds: Dataset, rid: int) -> Any:
    r = await s.get(ds.model, rid)
    if r is None or r.tenant_id != s.info["tenant_id"]:
        raise HTTPException(404, "Không tìm thấy bản ghi")
    return r


@router.put("/{key}/{rid}")
async def update(key: str, rid: int, body: RowIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    ds = _ds(key, user, "sua")
    tid = s.info["tenant_id"]
    r = await _get(s, ds, rid)
    groups = await _ind_groups(s, tid) if ds.nhom == "@indicator" else {}
    if ds.nhom == "@indicator":
        _check_row_perm(user, ds, "sua", groups.get(r.indicator_id))
    vals = await _values(s, tid, ds, body.data, creating=False)
    if ds.nhom == "@indicator" and "indicator_id" in vals:
        _check_row_perm(user, ds, "sua", groups.get(vals["indicator_id"]))
    before = _snap(ds, r)
    changed = {k: v for k, v in vals.items() if getattr(r, k) != v}
    if not changed:
        _, refs = await _options(s, tid, ds)
        return _row(ds, r, refs)
    locked = ds.confirm and getattr(r, ds.confirm.field) in ds.confirm.locked
    if locked and not body.ly_do.strip():
        raise HTTPException(422, "Bản ghi đã xác nhận/đối soát: ghi rõ lý do sửa")
    for k, v in changed.items():
        setattr(r, k, v)
    if locked:
        setattr(r, ds.confirm.field, ds.confirm.reset_to)
        for c in ds.confirm.clear:
            setattr(r, c, None)
    if hasattr(r, "version"):
        r.version = (r.version or 1) + 1
    if hasattr(r, "da_chinh_sua"):
        r.da_chinh_sua = True
    if ds.key == "so_lieu":
        r.thoi_diem_dong_bo = datetime.now(UTC)
        if body.ly_do.strip():
            r.ly_do = body.ly_do.strip()
    await _commit(s)
    await record_change(user, tid, f"du_lieu:{ds.key}:{rid}:sua", before, {**_snap(ds, r), "ly_do": body.ly_do.strip()})
    _, refs = await _options(s, tid, ds)
    return {**_row(ds, r, refs), "can_xac_nhan_lai": bool(locked)}


class DeleteIn(BaseModel):
    ids: list[int]
    ly_do: str


@router.post("/{key}/xoa")
async def delete(key: str, body: DeleteIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    """Xóa một hoặc nhiều bản ghi (bắt buộc lý do). Bản ghi bị xóa được lưu nguyên trạng trong nhật ký."""
    ds = _ds(key, user, "xoa")
    if not body.ly_do.strip():
        raise HTTPException(422, "Ghi rõ lý do xóa")
    if not body.ids or len(body.ids) > 500:
        raise HTTPException(422, "Chọn từ 1 đến 500 bản ghi")
    tid = s.info["tenant_id"]
    groups = await _ind_groups(s, tid) if ds.nhom == "@indicator" else {}
    rows_ = [await _get(s, ds, i) for i in dict.fromkeys(body.ids)]
    for r in rows_:
        if ds.nhom == "@indicator":
            _check_row_perm(user, ds, "xoa", groups.get(r.indicator_id))
    if ds.key == "chi_tieu":
        from app.indicators.models import IndicatorValue

        n = int((await s.execute(select(func.count(IndicatorValue.id)).where(IndicatorValue.indicator_id.in_([r.id for r in rows_])))).scalar() or 0)
        if n:
            raise HTTPException(409, f"Chỉ tiêu còn {n} số liệu; xóa số liệu trước hoặc giữ chỉ tiêu")
    snaps = [{"id": r.id, **_snap(ds, r)} for r in rows_]
    for r in rows_:
        await s.delete(r)
    await _commit(s)
    await record_change(user, tid, f"du_lieu:{ds.key}:xoa", {"ban_ghi": snaps}, {"ly_do": body.ly_do.strip(), "so_ban_ghi": len(snaps)})
    return {"da_xoa": len(snaps)}


@router.get("/{key}/csv")
async def export_csv(key: str, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> Response:
    ds = _ds(key, user)
    tid = s.info["tenant_id"]
    m = ds.model
    stmt = select(m).where(m.tenant_id == tid)
    if ds.nhom == "@indicator":
        groups = await _ind_groups(s, tid)
        stmt = stmt.where(m.indicator_id.in_([i for i, g in groups.items() if user.can("doc", g)] or [-1]))
    data = list((await s.execute(stmt.order_by(*[getattr(m, c) for c in ds.order], m.id))).scalars())
    _, refs = await _options(s, tid, ds)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", *[f.label for f in ds.fields], *(["Minh họa"] if ds.sample else [])])
    for r in data:
        row = _row(ds, r, refs)
        cells = []
        for f in ds.fields:
            v = row[f.name]
            if f.kind == "ref":
                v = row.get(f"{f.name}__nhan") or v
            elif f.kind == "enum" and f.options and v is not None:
                v = f.options.get(str(v), v)
            elif f.kind == "bool":
                v = "Có" if v else "Không"
            elif f.kind == "multi":
                v = ", ".join((f.options or {}).get(x, x) for x in v or [])
            elif f.kind == "refmulti":
                v = "; ".join(refs.get(f.ref or "", {}).get(x, str(x)) for x in v or [])
            cells.append("" if v is None else v)
        w.writerow([r.id, *cells, *(["Có" if row.get("is_sample") else ""] if ds.sample else [])])
    await record_change(user, tid, f"du_lieu:{ds.key}:xuat_csv", None, {"so_ban_ghi": len(data)})
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{ds.key}-{date.today().isoformat()}.csv"'})
