from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, require, tenant_db
from app.budget.models import BudgetLine
from app.budget.service import api_vs_closed
from app.compliance.models import ReconciliationMemo
from app.compliance.service import reminders, submission_report
from app.core.json import jsonable
from app.core.principal import CurrentUser

router = APIRouter(prefix="/api", tags=["tuan-thu-doi-soat"])
NHOM = {"ngan_sach": "ngan_sach", "giai_ngan": "dau_tu_cong", "cong_trinh": "cong_trinh"}


@router.get("/compliance")
async def compliance(tu: date = Query(default_factory=lambda: date.today() - timedelta(days=120)), den: date = Query(default_factory=date.today),
                     s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(get_current_user)) -> dict:
    return jsonable(await submission_report(s, s.info["tenant_id"], tu, den, date.today()))


@router.get("/reminders")
async def my_reminders(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> list:
    groups = {g for g, q in user.permissions.items() if "nhap" in q}
    if not groups:
        return []
    return jsonable(await reminders(s, s.info["tenant_id"], date.today(), groups))


class MemoIn(BaseModel):
    doi_tuong: str
    ref: str
    ky: str
    so_he_thong: float | None = None
    so_ho_so: float | None = None
    giai_trinh: str
    file_key: str | None = None


def memo_out(m: ReconciliationMemo) -> dict:
    return jsonable({"id": m.id, "doi_tuong": m.doi_tuong, "ref": m.ref, "ky": m.ky, "so_he_thong": m.so_he_thong, "so_ho_so": m.so_ho_so,
                     "chenh_lech": m.chenh_lech, "giai_trinh": m.giai_trinh, "file_key": m.file_key, "tao_luc": m.tao_luc})


@router.post("/reconciliation", status_code=201)
async def create_memo(body: MemoIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    nhom = NHOM.get(body.doi_tuong)
    if nhom is None:
        raise HTTPException(422, "Đối tượng đối soát không hợp lệ")
    if not (user.can("nhap", nhom) or user.can("duyet", nhom)):
        raise HTTPException(403, "Bạn không có quyền lập biên bản cho nhóm này")
    if not body.giai_trinh.strip():
        raise HTTPException(422, "Biên bản phải có nội dung giải trình")
    from decimal import Decimal

    a = Decimal(str(body.so_he_thong)) if body.so_he_thong is not None else None
    b = Decimal(str(body.so_ho_so)) if body.so_ho_so is not None else None
    m = ReconciliationMemo(tenant_id=s.info["tenant_id"], doi_tuong=body.doi_tuong, ref=body.ref, ky=body.ky, so_he_thong=a, so_ho_so=b,
                           chenh_lech=(a - b) if a is not None and b is not None else None, giai_trinh=body.giai_trinh.strip(),
                           file_key=body.file_key, nguoi_lap_id=user.id)
    s.add(m)
    await s.commit()
    await s.refresh(m)
    await record_change(user, m.tenant_id, f"bien_ban:{m.id}", None, memo_out(m))
    return memo_out(m)


@router.get("/reconciliation")
async def list_memos(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> list:
    rows = (await s.execute(select(ReconciliationMemo).where(ReconciliationMemo.tenant_id == s.info["tenant_id"]).order_by(ReconciliationMemo.id.desc()))).scalars()
    return [memo_out(m) for m in rows if user.can("doc", NHOM.get(m.doi_tuong, ""))]


class CloseIn(BaseModel):
    ky: str


@router.post("/budget/close")
async def close_budget_period(body: CloseIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(require("duyet", "ngan_sach"))) -> dict:
    """Chốt đối soát kỳ ngân sách: mọi chênh lệch API – báo cáo chốt phải có biên bản giải trình."""
    tid, nam = s.info["tenant_id"], int(body.ky[:4])
    diffs = await api_vs_closed(s, tid, nam, body.ky)
    have = set((await s.execute(select(ReconciliationMemo.ref).where(ReconciliationMemo.tenant_id == tid, ReconciliationMemo.doi_tuong == "ngan_sach",
                                                                     ReconciliationMemo.ky == body.ky))).scalars())
    need = [{"ref": f"{d['loai']}/{d['nhom_ma']}/{d['scope']}", **d} for d in diffs if f"{d['loai']}/{d['nhom_ma']}/{d['scope']}" not in have]
    if need:
        raise HTTPException(422, {"thong_bao": "Còn chênh lệch chưa có biên bản giải trình", "can_giai_trinh": jsonable(need)})
    r = await s.execute(update(BudgetLine).where(BudgetLine.tenant_id == tid, BudgetLine.ky == body.ky).values(trang_thai_doi_soat="da_doi_soat"))
    await s.commit()
    await record_change(user, tid, f"ngan_sach:chot_doi_soat:{body.ky}", None, {"so_dong": r.rowcount})
    return {"so_dong_da_doi_soat": r.rowcount}
