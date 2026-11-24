from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.engine import run_rules
from app.alerts.models import Alert, FollowUpCase
from app.alerts.rules import RULES
from app.audit.service import record_change
from app.auth.deps import get_current_user, require, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser

router = APIRouter(prefix="/api", tags=["canh-bao"])
MUC = {"cao": 0, "trung_binh": 1, "thap": 2}
OPEN = {"moi", "da_giao", "dang_xu_ly", "gia_han"}


def case_out(c: FollowUpCase | None) -> dict | None:
    if c is None:
        return None
    return {"id": c.id, "chi_dao": c.chi_dao, "co_quan_xu_ly": c.co_quan_xu_ly, "nguoi_phu_trach": c.nguoi_phu_trach, "nguyen_nhan": c.nguyen_nhan,
            "hanh_dong": c.hanh_dong, "han": c.han, "trang_thai": c.trang_thai, "ket_qua": c.ket_qua, "giao_luc": c.giao_luc,
            "cap_nhat_luc": c.cap_nhat_luc, "lich_su": c.lich_su}


def alert_out(a: Alert, c: FollowUpCase | None = None) -> dict:
    return {"id": a.id, "rule_ma": a.rule_ma, "quy_tac": RULES[a.rule_ma].ten if a.rule_ma in RULES else a.rule_ma,
            "can_cu": RULES[a.rule_ma].dt if a.rule_ma in RULES else "", "loai": a.loai, "nhom": a.nhom, "muc_do": a.muc_do,
            "tieu_de": a.tieu_de, "mo_ta": a.mo_ta, "link": a.link, "ky": a.ky, "trang_thai": a.trang_thai,
            "ghi_chu_chat_luong": a.ghi_chu_chat_luong, "phat_sinh_luc": a.phat_sinh_luc, "ho_so": case_out(c)}


async def _all(s: AsyncSession, user: CurrentUser) -> list[tuple[Alert, FollowUpCase | None]]:
    rows = (await s.execute(select(Alert, FollowUpCase).outerjoin(FollowUpCase, FollowUpCase.alert_id == Alert.id)
                            .where(Alert.tenant_id == s.info["tenant_id"]))).all()
    return [(a, c) for a, c in rows if user.can("doc", a.nhom)]


@router.get("/alerts")
async def alerts(loai: str | None = None, trang_thai: str | None = None, s: AsyncSession = Depends(tenant_db),
                 user: CurrentUser = Depends(get_current_user)) -> list:
    rows = await _all(s, user)
    rows = [(a, c) for a, c in rows if (not loai or a.loai == loai or (loai == "du_lieu_all" and a.loai != "tien_do"))
            and (not trang_thai or a.trang_thai == trang_thai) and (trang_thai or a.trang_thai != "het_hieu_luc")]
    rows.sort(key=lambda r: (MUC.get(r[0].muc_do, 9), -r[0].id))
    return jsonable([alert_out(a, c) for a, c in rows])


@router.get("/alerts/tuan-nay")
async def week(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> list:
    """Việc cần lãnh đạo chỉ đạo trong tuần (DT IV.1 khu ②): cảnh báo tiến độ đang mở + hồ sơ đến hạn trong 7 ngày."""
    today = date.today()
    rows = [(a, c) for a, c in await _all(s, user) if a.trang_thai in OPEN and (
        (a.loai == "tien_do" and a.muc_do in ("cao", "trung_binh")) or (c and (c.han - today).days <= 7))]
    rows.sort(key=lambda r: (MUC.get(r[0].muc_do, 9), r[1].han if r[1] else date.max, -r[0].id))
    return jsonable([alert_out(a, c) for a, c in rows[:12]])


@router.post("/alerts/run")
async def run(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(require("duyet", "canh_bao"))) -> dict:
    out = await run_rules(s, s.info["tenant_id"])
    await s.commit()
    return {"so_canh_bao": len(out)}


class AssignIn(BaseModel):
    co_quan_xu_ly: str
    nguoi_phu_trach: str
    han: date
    chi_dao: str = ""


@router.post("/alerts/{aid}/assign")
async def assign(aid: int, body: AssignIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(require("duyet", "canh_bao"))) -> dict:
    a = await s.get(Alert, aid)
    if a is None or not user.can("doc", a.nhom):
        raise HTTPException(404, "Không tìm thấy cảnh báo")
    if not body.co_quan_xu_ly.strip() or not body.nguoi_phu_trach.strip():
        raise HTTPException(422, "Cần ghi cơ quan xử lý và người phụ trách")
    c = (await s.execute(select(FollowUpCase).where(FollowUpCase.alert_id == aid))).scalar()
    if c is None:
        c = FollowUpCase(tenant_id=a.tenant_id, alert_id=aid, nguoi_giao_id=user.id, lich_su=[], han=body.han,
                         co_quan_xu_ly=body.co_quan_xu_ly, nguoi_phu_trach=body.nguoi_phu_trach)
        s.add(c)
    c.co_quan_xu_ly, c.nguoi_phu_trach, c.han, c.chi_dao, c.trang_thai = body.co_quan_xu_ly, body.nguoi_phu_trach, body.han, body.chi_dao, "da_giao"
    c.lich_su = [*c.lich_su, {"luc": datetime.now(UTC).isoformat(), "nguoi": user.username, "hanh_dong": "giao_xu_ly", "han": body.han.isoformat()}]
    a.trang_thai = "da_giao"
    await s.commit()
    await s.refresh(c)
    await record_change(user, a.tenant_id, f"canh_bao:{aid}:giao", None, jsonable(body.model_dump()))
    from app.noti.service import notify, users_by_name

    await notify(s, a.tenant_id, await users_by_name(a.tenant_id, c.nguoi_phu_trach), "giao_viec", f"Bạn được giao xử lý: {a.tieu_de}",
                 f"Hạn {c.han.strftime('%d/%m/%Y')}. {c.chi_dao or ''}".strip(), f"/canh-bao?id={aid}", "quan_trong", f"canh_bao_giao:{aid}", bo_qua=user.id)
    return jsonable(alert_out(a, c))


class CaseIn(BaseModel):
    trang_thai: str | None = None
    nguyen_nhan: str | None = None
    hanh_dong: str | None = None
    ket_qua: str | None = None
    han: date | None = None


@router.patch("/cases/{cid}")
async def update_case(cid: int, body: CaseIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    c = await s.get(FollowUpCase, cid)
    a = await s.get(Alert, c.alert_id) if c else None
    if c is None or a is None or not user.can("doc", a.nhom):
        raise HTTPException(404, "Không tìm thấy hồ sơ theo dõi")
    if not (user.can("nhap", a.nhom) or user.can("nhap", "canh_bao")):
        raise HTTPException(403, "Bạn không có quyền cập nhật hồ sơ này")
    before = case_out(c)
    for k in ("nguyen_nhan", "hanh_dong", "ket_qua"):
        if getattr(body, k) is not None:
            setattr(c, k, getattr(body, k).strip())
    if body.trang_thai:
        if body.trang_thai not in ("dang_xu_ly", "hoan_thanh", "gia_han"):
            raise HTTPException(422, "Trạng thái không hợp lệ")
        if body.trang_thai == "hoan_thanh" and not c.ket_qua:
            raise HTTPException(422, "Hoàn thành hồ sơ phải ghi kết quả xử lý")
        if body.trang_thai == "gia_han":
            if not body.han or body.han <= c.han:
                raise HTTPException(422, "Gia hạn phải ghi hạn mới")
            c.han = body.han
        c.trang_thai = a.trang_thai = body.trang_thai
    c.lich_su = [*c.lich_su, {"luc": datetime.now(UTC).isoformat(), "nguoi": user.username, "hanh_dong": body.trang_thai or "cap_nhat"}]
    await s.commit()
    await s.refresh(c)
    await record_change(user, a.tenant_id, f"ho_so:{cid}", jsonable(before), jsonable(case_out(c)))
    if body.trang_thai in ("hoan_thanh", "gia_han"):
        from app.noti.service import notify

        text = "đã hoàn thành" if body.trang_thai == "hoan_thanh" else f"gia hạn đến {c.han.strftime('%d/%m/%Y')}"
        await notify(s, a.tenant_id, [c.nguoi_giao_id], "ket_qua", f"Nhiệm vụ {text}: {a.tieu_de}", (c.ket_qua or "")[:300],
                     f"/canh-bao?id={a.id}", "thuong", bo_qua=user.id)
    return jsonable(case_out(c))
