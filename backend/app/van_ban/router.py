"""Văn bản chỉ đạo điều hành: danh sách, tra cứu, nhiệm vụ chỉ đạo được giao theo văn bản và tiến độ thực hiện."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.van_ban.models import VanBan

router = APIRouter(prefix="/api/van-ban", tags=["van-ban"])
LOAI = {"nghi_quyet": "Nghị quyết", "quyet_dinh": "Quyết định", "chi_thi": "Chỉ thị", "ke_hoach": "Kế hoạch", "thong_bao": "Thông báo kết luận",
        "cong_van": "Công văn", "bao_cao": "Báo cáo"}


async def _cases(s: AsyncSession, tid: int, ids: set[int], user: CurrentUser) -> dict[int, dict]:
    if not ids or not user.can("doc", "canh_bao"):
        return {}
    from app.alerts.models import Alert, FollowUpCase

    rows = (await s.execute(select(FollowUpCase, Alert.tieu_de).join(Alert, Alert.id == FollowUpCase.alert_id)
                            .where(FollowUpCase.tenant_id == tid, FollowUpCase.id.in_(ids)))).all()
    today = date.today()
    return {c.id: {"id": c.id, "tieu_de": t, "co_quan_xu_ly": c.co_quan_xu_ly, "han": c.han, "trang_thai": c.trang_thai,
                   "qua_han": c.trang_thai != "hoan_thanh" and c.han < today, "alert_id": c.alert_id} for c, t in rows}


def _out(v: VanBan, cases: dict[int, dict]) -> dict:
    nv = [cases[i] for i in v.nhiem_vu_ids or [] if i in cases]
    return {"id": v.id, "so_ky_hieu": v.so_ky_hieu, "ngay_ban_hanh": v.ngay_ban_hanh, "loai": v.loai, "loai_ten": LOAI.get(v.loai, v.loai),
            "co_quan_ban_hanh": v.co_quan_ban_hanh, "nguoi_ky": v.nguoi_ky, "trich_yeu": v.trich_yeu, "file_key": v.file_key, "lien_ket": v.lien_ket,
            "han_thuc_hien": v.han_thuc_hien, "trang_thai": v.trang_thai, "nhiem_vu": nv,
            "tien_do": {"tong": len(nv), "hoan_thanh": sum(1 for c in nv if c["trang_thai"] == "hoan_thanh"), "qua_han": sum(1 for c in nv if c["qua_han"])},
            "is_sample": v.is_sample}


@router.get("")
async def list_docs(q: str = "", loai: str = "", nhiem_vu: int | None = None, con_hieu_luc: bool = False,
                    s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    tid = s.info["tenant_id"]
    stmt = select(VanBan).where(VanBan.tenant_id == tid)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(VanBan.so_ky_hieu).like(like), func.lower(VanBan.trich_yeu).like(like), func.lower(VanBan.co_quan_ban_hanh).like(like)))
    if loai:
        stmt = stmt.where(VanBan.loai == loai)
    if con_hieu_luc:
        stmt = stmt.where(VanBan.trang_thai == "con_hieu_luc")
    rows = list((await s.execute(stmt.order_by(VanBan.ngay_ban_hanh.desc(), VanBan.id.desc()))).scalars())
    if nhiem_vu is not None:
        rows = [v for v in rows if nhiem_vu in (v.nhiem_vu_ids or [])]
    cases = await _cases(s, tid, {i for v in rows for i in v.nhiem_vu_ids or []}, user)
    can_edit = user.can("duyet", "canh_bao") or user.can("duyet", "quan_tri")
    return jsonable({"van_ban": [_out(v, cases) for v in rows], "loai": LOAI, "co_quyen_sua": can_edit and "man_hinh_tv" not in user.roles})
