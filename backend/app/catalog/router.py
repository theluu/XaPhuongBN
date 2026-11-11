from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, tenant_db
from app.catalog.models import Indicator, Program, Scenario
from app.catalog.service import program_progress
from app.core.num import num
from app.core.principal import CurrentUser
from app.indicators.service import card

router = APIRouter(prefix="/api", tags=["nhiem-vu-kich-ban"])


@router.get("/programs")
async def programs(ky: str | None = None, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    ky = ky or date.today().strftime("%Y-%m")
    tid = s.info["tenant_id"]
    inds = {i.id: i for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tid))).scalars()}
    out = []
    for p in (await s.execute(select(Program).where(Program.tenant_id == tid).order_by(Program.ma))).scalars():
        cards = [await card(s, inds[i], ky) for i in p.indicator_ids if i in inds]
        prog = program_progress(p, {c["id"]: c["status"] for c in cards if c["status"] != "theo_doi"})
        visible = [c for c in cards if user.can("doc", c["nhom"])]
        out.append({"id": p.id, "ma": p.ma, "ten": p.ten, "mo_ta": p.mo_ta, "don_vi_chu_tri": p.don_vi_chu_tri,
                    "trang_thai": p.trang_thai, "tien_do": {**prog, "ty_le_dat_pct": num(prog["ty_le_dat_pct"])},
                    "chi_tieu": visible})
    return out


@router.get("/scenarios")
async def scenarios(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(get_current_user)) -> list[dict]:
    rows = (await s.execute(select(Scenario).where(Scenario.tenant_id == s.info["tenant_id"]).order_by(Scenario.la_bo_sung, Scenario.id))).scalars()
    return [{"id": x.id, "ma": x.ma, "ten": x.ten, "mo_ta": x.mo_ta, "la_bo_sung": x.la_bo_sung, "trang_thai": x.trang_thai,
             "so_chi_tieu": len(x.indicator_ids), "indicator_ids": x.indicator_ids, "rule_codes": x.rule_codes, "layout": x.layout}
            for x in rows]
