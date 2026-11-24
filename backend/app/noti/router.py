"""Chuông thông báo: danh sách, số chưa đọc, đánh dấu đã đọc."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.noti.models import Noti

router = APIRouter(prefix="/api/noti", tags=["thong-bao-ca-nhan"])


def _out(n: Noti) -> dict:
    return {"id": n.id, "loai": n.loai, "tieu_de": n.tieu_de, "noi_dung": n.noi_dung, "lien_ket": n.lien_ket, "muc_do": n.muc_do,
            "tao_luc": n.tao_luc, "da_doc": n.da_doc_luc is not None}


@router.get("")
async def list_noti(chi_chua_doc: bool = False, limit: int = 40, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    q = select(Noti).where(Noti.user_id == user.id)
    if chi_chua_doc:
        q = q.where(Noti.da_doc_luc.is_(None))
    rows = list((await s.execute(q.order_by(Noti.tao_luc.desc(), Noti.id.desc()).limit(max(1, min(limit, 100))))).scalars())
    n = (await s.execute(select(func.count(Noti.id)).where(Noti.user_id == user.id, Noti.da_doc_luc.is_(None)))).scalar()
    return jsonable({"chua_doc": int(n or 0), "muc": [_out(x) for x in rows]})


@router.get("/dem")
async def count(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    n = (await s.execute(select(func.count(Noti.id)).where(Noti.user_id == user.id, Noti.da_doc_luc.is_(None)))).scalar()
    last = (await s.execute(select(Noti).where(Noti.user_id == user.id, Noti.da_doc_luc.is_(None)).order_by(Noti.tao_luc.desc(), Noti.id.desc()).limit(1))).scalar()
    return jsonable({"chua_doc": int(n or 0), "moi_nhat": _out(last) if last else None})


@router.post("/{nid}/doc")
async def read_one(nid: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    n = await s.get(Noti, nid)
    if n is None or n.user_id != user.id:
        raise HTTPException(404, "Không tìm thấy thông báo")
    if n.da_doc_luc is None:
        n.da_doc_luc = datetime.now(UTC)
        await s.commit()
    return {"ok": True}


@router.post("/doc-het")
async def read_all(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    r = await s.execute(update(Noti).where(Noti.user_id == user.id, Noti.da_doc_luc.is_(None)).values(da_doc_luc=datetime.now(UTC)))
    await s.commit()
    return {"da_doc": r.rowcount or 0}
