from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require, tenant_db
from app.catalog.models import Indicator
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.indicators.service import card
from app.platform.models import ResidentialGroup
from app.quality_of_life.models import PointOfInterest
from app.services_pakn.models import FeedbackTicket

router = APIRouter(prefix="/api/qol", tags=["giao-duc-y-te-moi-truong"])
DOC = require("doc", "gd_yt_mt")
NHOM = {"giao_duc": {"NQ01-11", "DT-HS", "DT-LOP", "DT-TRUONG"}, "y_te": {"NQ01-12"}, "moi_truong": {"NQ01-14", "NQ01-15", "NQ01-16"}}
LOAI = {"truong", "tram_y_te", "diem_moi_truong"}


@router.get("/summary")
async def summary(ky: str = Query(default_factory=lambda: date.today().strftime("%Y-%m")), s: AsyncSession = Depends(tenant_db),
                  _: CurrentUser = Depends(DOC)) -> dict:
    inds = (await s.execute(select(Indicator).where(Indicator.tenant_id == s.info["tenant_id"], Indicator.phan_he == "gd_yt_mt").order_by(Indicator.ma_chi_tieu))).scalars()
    out: dict[str, list] = {k: [] for k in NHOM} | {"khac": []}
    for i in inds:
        c = await card(s, i, ky)
        out[next((k for k, v in NHOM.items() if i.ma_chi_tieu in v), "khac")].append(c)
    return jsonable(out)


@router.get("/layers/{loai}")
async def layer(loai: str, s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> dict:
    if loai not in LOAI:
        raise HTTPException(422, "Lớp bản đồ không hợp lệ")
    rows = (await s.execute(select(PointOfInterest).where(PointOfInterest.tenant_id == s.info["tenant_id"], PointOfInterest.loai == loai,
                                                          PointOfInterest.cho_phep_hien_thi, PointOfInterest.chat_luong_du_lieu == "dat"))).scalars()
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(p.lng), float(p.lat)]},
         "properties": {"ten": p.ten, "loai": p.loai, **(p.thuoc_tinh or {})}} for p in rows]}


@router.get("/env-feedback")
async def env_feedback(tu: date = Query(default_factory=lambda: date.today() - timedelta(days=90)), den: date = Query(default_factory=date.today),
                       s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(DOC)) -> list:
    tid = s.info["tenant_id"]
    names = {g.id: g.ten for g in (await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == tid))).scalars()}
    rows = (await s.execute(select(FeedbackTicket.tdp_id).where(FeedbackTicket.tenant_id == tid, FeedbackTicket.linh_vuc == "moi_truong",
                                                                 FeedbackTicket.ngay_nhan >= tu, FeedbackTicket.ngay_nhan <= den))).scalars()
    cnt = Counter(names.get(r, "Chưa xác định địa bàn") if r else "Chưa xác định địa bàn" for r in rows)
    return [{"khu_vuc": k, "so_phan_anh": v} for k, v in cnt.most_common()]
