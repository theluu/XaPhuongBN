"""Lịch công tác tuần của lãnh đạo: xem theo tuần, lịch hôm nay cho trang chủ và màn hình TV. Thêm/sửa/xóa tại Quản lý dữ liệu."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.lich.models import LichCongTac

router = APIRouter(prefix="/api/lich-cong-tac", tags=["lich-cong-tac"])
LOAI = {"hop": "Họp", "lam_viec": "Làm việc", "tiep_dan": "Tiếp công dân", "kiem_tra": "Kiểm tra", "cong_tac": "Công tác", "khac": "Khác"}
TT = {"chinh_thuc": "Chính thức", "du_kien": "Dự kiến", "hoan": "Hoãn"}
THU = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


def _out(x: LichCongTac, tv: bool) -> dict:
    return {"id": x.id, "ngay": x.ngay, "gio_bat_dau": x.gio_bat_dau, "gio_ket_thuc": x.gio_ket_thuc, "noi_dung": x.noi_dung, "chu_tri": x.chu_tri,
            "dia_diem": x.dia_diem, "thanh_phan": "" if tv else x.thanh_phan, "don_vi_chuan_bi": "" if tv else x.don_vi_chuan_bi,
            "loai": x.loai, "loai_ten": LOAI.get(x.loai, x.loai), "trang_thai": x.trang_thai, "trang_thai_ten": TT.get(x.trang_thai, x.trang_thai),
            "ghi_chu": "" if tv else x.ghi_chu, "is_sample": x.is_sample}


@router.get("")
async def week(tuan: date | None = None, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    """`tuan`: một ngày bất kỳ trong tuần cần xem (mặc định tuần hiện tại, Thứ Hai → Chủ Nhật)."""
    d = tuan or date.today()
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=6)
    tv = "man_hinh_tv" in user.roles
    q = select(LichCongTac).where(LichCongTac.tenant_id == s.info["tenant_id"], LichCongTac.ngay >= start, LichCongTac.ngay <= end)
    if tv:
        q = q.where(LichCongTac.hien_tren_tv.is_(True))
    rows = list((await s.execute(q.order_by(LichCongTac.ngay, LichCongTac.gio_bat_dau, LichCongTac.id))).scalars())
    days = [{"ngay": start + timedelta(days=i), "thu": THU[i], "muc": [_out(x, tv) for x in rows if x.ngay == start + timedelta(days=i)]} for i in range(7)]
    can_edit = user.can("duyet", "canh_bao") or user.can("duyet", "quan_tri")
    return jsonable({"tu": start, "den": end, "tuan_so": start.isocalendar().week, "ngay": days, "hom_nay": date.today(), "co_quyen_sua": can_edit and not tv})


@router.get("/hom-nay")
async def today(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> list:
    tv = "man_hinh_tv" in user.roles
    q = select(LichCongTac).where(LichCongTac.tenant_id == s.info["tenant_id"], LichCongTac.ngay == date.today(), LichCongTac.trang_thai != "hoan")
    if tv:
        q = q.where(LichCongTac.hien_tren_tv.is_(True))
    return jsonable([_out(x, tv) for x in (await s.execute(q.order_by(LichCongTac.gio_bat_dau))).scalars()])


def check_time(v: str | None) -> None:
    if v and not (len(v) == 5 and v[2] == ":" and v[:2].isdigit() and v[3:].isdigit() and int(v[:2]) < 24 and int(v[3:]) < 60):
        raise HTTPException(422, "Giờ theo dạng HH:MM, VD 08:00")
