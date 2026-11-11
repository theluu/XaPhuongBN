from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_change
from app.auth.deps import get_current_user, require, tenant_db
from app.catalog.models import Indicator
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.files.models import StoredFile
from app.files.storage import IMAGE_TYPES
from app.indicators.service import card
from app.works.models import Work, WorkProgress
from app.works.service import (behind_schedule, list_works, missing_decision_dossier, prog_out, stale_works, valid_points,
                               work_row)

router = APIRouter(prefix="/api/works", tags=["cong-trinh"])
DOC = require("doc", "cong_trinh")


@router.get("")
async def works(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> list:
    return jsonable(await list_works(s, s.info["tenant_id"]))


@router.get("/summary")
async def works_summary(ky: str = Query(default_factory=lambda: date.today().strftime("%Y-%m")), s: AsyncSession = Depends(tenant_db),
                        user: CurrentUser = Depends(DOC)) -> dict:
    tid, today = s.info["tenant_id"], date.today()
    rows = await list_works(s, tid, today)
    inds = (await s.execute(select(Indicator).where(Indicator.tenant_id == tid, Indicator.phan_he == "cong_trinh").order_by(Indicator.ma_chi_tieu))).scalars()
    return jsonable({
        "so_cong_trinh": len(rows), "so_cham": sum(1 for r in rows if r["moi_nhat"] and r["moi_nhat"]["cham"]),
        "so_tre_han": sum(1 for r in rows if r["tre_han_ngay"]), "so_can_quyet_dinh": len(await missing_decision_dossier(s, tid)),
        "so_chua_cap_nhat": len(await stale_works(s, tid, today)),
        "chi_tieu_do_thi": [await card(s, i, ky) for i in inds if user.can("doc", i.nhom)],
        "diem_nghen": await behind_schedule(s, tid, today),
    })


@router.get("/geojson")
async def geojson(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> dict:
    out = []
    for w in await valid_points(s, s.info["tenant_id"]):
        r = await work_row(s, w)
        m = r["moi_nhat"]
        out.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(w.lng), float(w.lat)]},
                    "properties": {"ma": w.ma_cong_trinh, "ten": w.ten, "loai": "cong_trinh", "cham": bool(m and m["cham"]),
                                   "tre_han": bool(r["tre_han_ngay"]), "thuc_te_pct": float(m["thuc_te_pct"]) if m and m["thuc_te_pct"] is not None else None}})
    return {"type": "FeatureCollection", "features": out}


async def _work(s: AsyncSession, ma: str) -> Work:
    w = (await s.execute(select(Work).where(Work.tenant_id == s.info["tenant_id"], Work.ma_cong_trinh == ma))).scalar()
    if w is None:
        raise HTTPException(404, "Không tìm thấy công trình")
    return w


@router.get("/{ma}")
async def work_detail(ma: str, s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> dict:
    w = await _work(s, ma)
    hist = (await s.execute(select(WorkProgress).where(WorkProgress.work_id == w.id).order_by(WorkProgress.ngay, WorkProgress.id))).scalars()
    return jsonable({**await work_row(s, w), "tien_do": [prog_out(p) for p in hist]})


class ProgressIn(BaseModel):
    ngay: date
    ke_hoach_pct: float | None = None
    thuc_te_pct: float | None = None
    gpmb: str = ""
    vuong_mac: str = ""
    can_quyet_dinh: bool = False
    anh_keys: list[str] = []
    minh_chung_keys: list[str] = []


@router.post("/{ma}/progress", status_code=201)
async def add_progress(ma: str, body: ProgressIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(require("nhap", "cong_trinh"))) -> dict:
    w = await _work(s, ma)
    keys = body.anh_keys + body.minh_chung_keys
    files = {f.key: f for f in (await s.execute(select(StoredFile).where(StoredFile.key.in_(keys)))).scalars()} if keys else {}
    if set(keys) - set(files):
        raise HTTPException(422, "Tệp đính kèm không tồn tại")
    if any(files[k].content_type not in IMAGE_TYPES for k in body.anh_keys):
        raise HTTPException(422, "Ảnh hiện trường phải là tệp ảnh (JPG, PNG, WEBP)")
    for v in (body.ke_hoach_pct, body.thuc_te_pct):
        if v is not None and not 0 <= v <= 100:
            raise HTTPException(422, "Tiến độ phải trong khoảng 0–100%")
    p = WorkProgress(work_id=w.id, tenant_id=w.tenant_id, nguoi_nhap_id=user.id, trang_thai_xac_nhan="tam_thoi", **body.model_dump())
    s.add(p)
    await s.commit()
    await record_change(user, w.tenant_id, f"cong_trinh:{ma}:tien_do:{p.id}", None, jsonable(prog_out(p)))
    return jsonable(prog_out(p))


@router.post("/progress/{pid}/confirm")
async def confirm_progress(pid: int, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    p = await s.get(WorkProgress, pid)
    if p is None:
        raise HTTPException(404, "Không tìm thấy báo cáo tiến độ")
    if not user.can("duyet", "cong_trinh"):
        raise HTTPException(403, "Bạn không có quyền xác nhận tiến độ công trình")
    if p.nguoi_nhap_id == user.id:
        raise HTTPException(403, "Người nhập không được tự xác nhận")
    if not (p.anh_keys or p.minh_chung_keys):
        raise HTTPException(422, "Tiến độ công trình cần có minh chứng (ảnh hiện trường hoặc biên bản)")
    p.trang_thai_xac_nhan, p.nguoi_xac_nhan_id = "da_xac_nhan", user.id
    await s.commit()
    await record_change(user, p.tenant_id, f"cong_trinh:tien_do:{pid}:xac_nhan", {"trang_thai": "tam_thoi"}, {"trang_thai": "da_xac_nhan"})
    return jsonable(prog_out(p))
