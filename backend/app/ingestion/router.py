import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, tenant_db
from app.catalog.models import Indicator
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.ingestion.models import ImportBatch
from app.ingestion.specs import SPECS, Spec, parse_cell, validate_row, write_row
from app.platform.models import SharedCatalog
from app.projects.models import Project

router = APIRouter(prefix="/api/import", tags=["nhap-lieu"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_ROWS = 5000


def _spec(loai: str, user: CurrentUser) -> Spec:
    spec = SPECS.get(loai)
    if spec is None:
        raise HTTPException(404, "Không có biểu mẫu này")
    if spec.nhom != "*" and not user.can("nhap", spec.nhom):
        raise HTTPException(403, "Bạn không có quyền nhập số liệu nhóm này")
    if spec.nhom == "*" and not any("nhap" in q for q in user.permissions.values()):
        raise HTTPException(403, "Bạn không có quyền nhập số liệu")
    return spec


@router.get("/templates/{loai}/spec")
async def spec_json(loai: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    sp = _spec(loai, user)
    return {"loai": sp.loai, "ten": sp.ten, "huong_dan": sp.huong_dan,
            "cot": [{"ten": c.ten, "kieu": c.kieu, "bat_buoc": c.bat_buoc, "lua_chon": c.lua_chon, "goi_y": c.goi_y} for c in sp.cot]}


@router.get("/templates/{loai}")
async def template(loai: str, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> Response:
    sp = _spec(loai, user)
    wb = Workbook()
    ws = wb.active
    ws.title = "Dữ liệu"
    ws.append([c.ten for c in sp.cot])
    for i, c in enumerate(sp.cot, start=1):
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF" if c.bat_buoc else "16324A")
        cell.fill = PatternFill("solid", fgColor="16324A" if c.bat_buoc else "DCE3E8")
        ws.column_dimensions[cell.column_letter].width = max(14, len(c.ten) + 4)
        if c.lua_chon:
            dv = DataValidation(type="list", formula1='"' + ",".join(c.lua_chon) + '"', allow_blank=not c.bat_buoc)
            ws.add_data_validation(dv)
            dv.add(f"{cell.column_letter}2:{cell.column_letter}{MAX_ROWS}")
    g = wb.create_sheet("Hướng dẫn")
    g.append([sp.ten])
    g["A1"].font = Font(bold=True, size=13)
    for line in sp.huong_dan:
        g.append([line])
    g.append([])
    g.append(["Cột", "Bắt buộc", "Kiểu", "Gợi ý"])
    for c in sp.cot:
        g.append([c.ten, "Có" if c.bat_buoc else "", {"so": "Số", "ngay": "Ngày", "ky": "Kỳ", "lua_chon": "Chọn"}.get(c.kieu, "Chữ"), c.goi_y])
    g.column_dimensions["A"].width = 70
    dm = wb.create_sheet("Danh mục")
    tid = s.info["tenant_id"]
    if loai == "chi_tieu":
        for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tid).order_by(Indicator.ma_chi_tieu))).scalars():
            if user.can("nhap", i.nhom):
                dm.append([i.ma_chi_tieu, i.ten, i.don_vi_do, i.ky_cap_nhat])
    elif loai == "giai_ngan":
        for p in (await s.execute(select(Project).where(Project.tenant_id == tid).order_by(Project.ma_du_an))).scalars():
            dm.append([p.ma_du_an, p.ten])
    elif loai == "ngan_sach":
        for c in (await s.execute(select(SharedCatalog).where(SharedCatalog.loai.in_(["nhom_thu", "nhom_chi", "nhiem_vu_chi"])).order_by(SharedCatalog.loai))).scalars():
            dm.append([c.ma, c.ten, c.loai])
    buf = io.BytesIO()
    wb.save(buf)
    return Response(buf.getvalue(), media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="bieu_mau_{loai}.xlsx"'})


def _read(raw: bytes, name: str) -> list[list]:
    if raw[:4] == b"PK\x03\x04":
        try:
            wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(422, "Tệp Excel bị lỗi, không đọc được") from e
        ws = wb["Dữ liệu"] if "Dữ liệu" in wb.sheetnames else wb.active
        return [list(r) for r in ws.iter_rows(values_only=True)]
    if name.lower().endswith(".csv"):
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise HTTPException(422, "Tệp CSV phải dùng mã UTF-8") from e
        delim = ";" if text.split("\n", 1)[0].count(";") > text.split("\n", 1)[0].count(",") else ","
        return [r for r in csv.reader(io.StringIO(text), delimiter=delim)]
    raise HTTPException(422, "Chỉ nhận tệp Excel (.xlsx) hoặc CSV")


async def _check(s: AsyncSession, user: CurrentUser, sp: Spec, records: list[tuple[int, dict]]) -> tuple[list[dict], list[dict]]:
    ok, loi, cache = [], [], {}
    for dong, raw in records:
        if not any(v not in (None, "") for v in raw.values()):
            continue
        row, errs = {}, []
        for c in sp.cot:
            try:
                row[c.ten] = parse_cell(c, raw.get(c.ten))
            except ValueError as e:
                errs.append((c.ten, str(e)))
                row[c.ten] = None
            if c.bat_buoc and row[c.ten] in (None, "") and not any(x[0] == c.ten for x in errs):
                errs.append((c.ten, f"Bắt buộc nhập {c.ten.lower()}"))
        if not errs:
            errs = await validate_row(s, user, sp, row, cache)
        if errs:
            loi += [{"dong": dong, "cot": c, "thong_bao": m} for c, m in errs]
        else:
            ok.append({"dong": dong, **jsonable(row)})
    return ok, loi


@router.post("/{loai}/preview")
async def preview(loai: str, file: UploadFile = File(...), s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    sp = _spec(loai, user)
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(422, "Tệp vượt quá 10 MB")
    rows = _read(raw, file.filename or "")
    header = [str(c or "").strip() for c in (rows[0] if rows else [])]
    names = [c.ten for c in sp.cot]
    if header[: len(names)] != names:
        raise HTTPException(422, "Tệp không đúng biểu mẫu. Hãy tải biểu mẫu mới nhất và giữ nguyên dòng tiêu đề.")
    if len(rows) - 1 > MAX_ROWS:
        raise HTTPException(422, f"Tối đa {MAX_ROWS} dòng mỗi lần nhập")
    records = [(i, dict(zip(names, r))) for i, r in enumerate(rows[1:], start=2)]
    ok, loi = await _check(s, user, sp, records)
    b = ImportBatch(tenant_id=s.info["tenant_id"], loai=loai, ten_tep=(file.filename or "tep")[:300], rows=ok, loi=loi, nguoi_tao_id=user.id)
    s.add(b)
    await s.commit()
    return {"preview_id": b.id, "hop_le": len(ok), "loi": loi, "mau": ok[:20]}


class CommitIn(BaseModel):
    preview_id: int


async def _commit(s: AsyncSession, user: CurrentUser, sp: Spec, b: ImportBatch) -> int:
    cache: dict = {}
    parsed = []
    for r in b.rows:
        row = {c.ten: parse_cell(c, r.get(c.ten)) for c in sp.cot}
        if await validate_row(s, user, sp, row, cache):  # kiểm tra lại khi nhập (dữ liệu có thể đổi sau xem trước)
            raise HTTPException(422, f"Dòng {r['dong']} không còn hợp lệ, hãy xem trước lại")
        parsed.append(row)
    for row in parsed:
        await write_row(s, user, sp, row, b.ten_tep, cache)
    b.trang_thai = "da_nhap"
    await s.commit()
    await record_change(user, b.tenant_id, f"nhap_tep:{sp.loai}:{b.id}", None, {"ten_tep": b.ten_tep, "so_dong": len(parsed)})
    return len(parsed)


@router.post("/{loai}/commit")
async def commit(loai: str, body: CommitIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    sp = _spec(loai, user)
    b = await s.get(ImportBatch, body.preview_id)
    if b is None or b.loai != loai or b.nguoi_tao_id != user.id:
        raise HTTPException(404, "Không tìm thấy lần xem trước")
    if b.trang_thai == "da_nhap":
        raise HTTPException(409, "Tệp này đã được nhập")
    if b.loi:
        raise HTTPException(422, "Tệp còn lỗi, sửa và tải lên lại. Không dòng nào được nhập.")
    return {"da_nhap": await _commit(s, user, sp, b)}


class RowsIn(BaseModel):
    rows: list[dict]


@router.post("/{loai}/rows")
async def rows(loai: str, body: RowsIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    """Biểu mẫu động: cùng đặc tả và kiểm tra với tệp Excel."""
    sp = _spec(loai, user)
    ok, loi = await _check(s, user, sp, [(i, r) for i, r in enumerate(body.rows, start=1)])
    if loi:
        raise HTTPException(422, {"loi": loi})
    b = ImportBatch(tenant_id=s.info["tenant_id"], loai=loai, ten_tep="Biểu mẫu trực tuyến", rows=ok, loi=[], nguoi_tao_id=user.id)
    s.add(b)
    await s.flush()
    return {"da_nhap": await _commit(s, user, sp, b)}
