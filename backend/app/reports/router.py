from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models import Alert, FollowUpCase
from app.audit.service import record_change
from app.auth.deps import get_current_user, require, tenant_db
from app.auth.models import User
from app.catalog.models import Indicator
from app.core.db import admin_sessionmaker
from app.core.format_vn import vn
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.files import storage
from app.files.models import StoredFile
from app.indicators.service import card
from app.platform.models import Tenant
from app.platform.router import agency_name, sample_flag
from app.reports.models import MeetingSession
from app.reports.pdf import render_minutes

router = APIRouter(prefix="/api/reports", tags=["bao-cao"])
LOAI = {"tien_do": "Tiến độ", "qua_han": "Quá hạn cập nhật", "lech_nguon": "Lệch nguồn", "du_lieu": "Thiếu hồ sơ", "chua_gui": "Chưa gửi dữ liệu"}
MUC = {"cao": "Cao", "trung_binh": "Trung bình", "thap": "Thấp"}
TT = {"da_giao": "Đã giao", "dang_xu_ly": "Đang xử lý", "hoan_thanh": "Hoàn thành", "gia_han": "Gia hạn"}


def _ky_ten(ky: str) -> str:
    if len(ky) == 7 and ky[5] == "Q":
        return f"Quý {['', 'I', 'II', 'III', 'IV'][int(ky[6])]}/{ky[:4]}"
    if len(ky) == 7:
        return f"Tháng {int(ky[5:7])}/{ky[:4]}"
    return f"Năm {ky}" if len(ky) == 4 else ky


class MinutesIn(BaseModel):
    ky: str
    thanh_phan: str = ""
    ket_luan: str = ""


@router.post("/bien-ban-giao-ban")
async def minutes(body: MinutesIn, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(require("duyet", "canh_bao"))) -> Response:
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as adm:
        t = await adm.get(Tenant, tid)
        u = await adm.get(User, user.id)
    nq = [await card(s, i, body.ky) for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tid))).scalars() if "NQ01" in (i.bo or [])]
    rows = (await s.execute(select(Alert, FollowUpCase).outerjoin(FollowUpCase, FollowUpCase.alert_id == Alert.id)
                            .where(Alert.tenant_id == tid, Alert.trang_thai != "het_hieu_luc").order_by(Alert.id))).all()
    giao = [(a, c) for a, c in rows if c is not None]
    done = [(a, c) for a, c in giao if c.trang_thai == "hoan_thanh"]
    data = {
        "co_quan": agency_name(t), "ky": body.ky, "ky_ten": _ky_ten(body.ky), "ngay": date.today().strftime("%d/%m/%Y"),
        "thanh_phan": body.thanh_phan, "ket_luan": body.ket_luan, "co_minh_hoa": (await sample_flag(s))["co_du_lieu_minh_hoa"],
        "nq01": {"tong": len(nq), **{k: sum(c["status"] == k for c in nq) for k in ("dat", "nguy_co", "chua_du_du_lieu")}},
        "chi_tieu_nguy_co": [[c["ten"], _ky_ten(c["ky"]), f"{vn(c['thuc_hien'])} {c['don_vi']}", vn(c["muc_so_sanh"])] for c in nq if c["status"] == "nguy_co"],
        "canh_bao": [[a.tieu_de, LOAI.get(a.loai, a.loai), MUC.get(a.muc_do, a.muc_do)] for a, _ in rows],
        "giao": [[a.tieu_de, c.co_quan_xu_ly, c.nguoi_phu_trach, c.han.strftime("%d/%m/%Y"), TT.get(c.trang_thai, c.trang_thai)] for a, c in giao],
        "ket_qua": [[a.tieu_de, c.ket_qua] for a, c in done],
        "lap_luc": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M %d/%m/%Y"), "nguoi_lap": f"{u.chuc_danh} {u.ho_ten}" if u else user.username,
    }
    pdf = render_minutes(data)
    key = storage.save(tid, pdf, "application/pdf")
    s.add(StoredFile(tenant_id=tid, key=key, ten_goc=f"bien-ban-giao-ban-{body.ky}.pdf", content_type="application/pdf", kich_thuoc=len(pdf), nguoi_tai_len_id=user.id))
    m = MeetingSession(tenant_id=tid, ngay=date.today(), ky=body.ky, thanh_phan=body.thanh_phan, ket_luan=body.ket_luan, so_canh_bao=len(rows),
                       so_giao=len(giao), so_hoan_thanh=len(done), noi_dung={"nq01": data["nq01"]}, file_key=key, nguoi_lap_id=user.id)
    s.add(m)
    await s.commit()
    await record_change(user, tid, f"bien_ban_giao_ban:{m.id}", None, {"ky": body.ky, "so_canh_bao": m.so_canh_bao, "so_giao": m.so_giao, "so_hoan_thanh": m.so_hoan_thanh})
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="bien-ban-giao-ban-{body.ky}.pdf"'})


@router.get("/giao-ban")
async def sessions(s: AsyncSession = Depends(tenant_db), _: CurrentUser = Depends(get_current_user)) -> list:
    rows = (await s.execute(select(MeetingSession).where(MeetingSession.tenant_id == s.info["tenant_id"]).order_by(MeetingSession.id.desc()))).scalars()
    return jsonable([{"id": m.id, "ngay": m.ngay, "ky": m.ky, "so_canh_bao": m.so_canh_bao, "so_giao": m.so_giao, "so_hoan_thanh": m.so_hoan_thanh,
                      "file_key": m.file_key, "thanh_phan": m.thanh_phan} for m in rows])
