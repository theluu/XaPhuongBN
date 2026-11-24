"""Dải bản tin dưới đầu trang: thông báo điều hành đang hiệu lực + tin vận hành tự sinh (không có thông tin cá nhân)
và liên kết nhanh tới Cổng TTĐT, Dịch vụ công… (tham khảo bố cục Cổng TTĐT phường Việt Yên, thành phố Bắc Ninh)."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, tenant_db
from app.core.json import jsonable
from app.core.principal import CurrentUser
from app.platform.models import Tenant
from app.thong_bao.models import ThongBao

router = APIRouter(prefix="/api", tags=["bang-tin"])
MUC = {"khan": 0, "quan_trong": 1, "thuong": 2}
LIEN_KET_CHUNG = [{"ten": "Dịch vụ công quốc gia", "url": "https://dichvucong.gov.vn"}]
LIEN_KET_TINH = {"Bắc Ninh": [{"ten": "Cổng TTĐT thành phố Bắc Ninh", "url": "https://bacninh.gov.vn"}]}


def default_links(t: Tenant) -> list[dict]:
    cfg = t.config or {}
    return [*([{"ten": f"Cổng TTĐT {t.ten[0].lower() + t.ten[1:]}", "url": cfg["cong_ttdt"]}] if cfg.get("cong_ttdt") else []),
            *LIEN_KET_TINH.get(cfg.get("tinh", ""), []), *LIEN_KET_CHUNG]


async def _auto(s: AsyncSession, user: CurrentUser, tid: int, today: date) -> list[dict]:
    """Tin vận hành tự sinh theo quyền người xem: chỉ số đếm, không nêu tên người."""
    out: list[dict] = []
    if user.can("doc", "tthc_pakn"):
        from app.field_reports.models import FieldReport
        from app.field_reports.service import DONG

        open_ = (FieldReport.tenant_id == tid, FieldReport.trang_thai.not_in(DONG))
        khan = int((await s.execute(select(func.count(FieldReport.id)).where(*open_, FieldReport.khan_cap.is_(True)))).scalar() or 0)
        qh = int((await s.execute(select(func.count(FieldReport.id)).where(*open_, FieldReport.han_xu_ly < today))).scalar() or 0)
        moi = int((await s.execute(select(func.count(FieldReport.id)).where(FieldReport.tenant_id == tid, FieldReport.trang_thai == "moi"))).scalar() or 0)
        if khan:
            out.append({"loai": "van_hanh", "muc_do": "khan", "tieu_de": f"{khan} phản ánh khẩn cấp đang xử lý", "lien_ket": "/?loc=moi"})
        if qh:
            out.append({"loai": "van_hanh", "muc_do": "quan_trong", "tieu_de": f"{qh} phản ánh hiện trường quá hạn xử lý", "lien_ket": "/?loc=qua_han"})
        if moi:
            out.append({"loai": "van_hanh", "muc_do": "thuong", "tieu_de": f"{moi} phản ánh mới chưa giao xử lý", "lien_ket": "/?loc=moi"})
    if user.can("doc", "canh_bao"):
        from app.alerts.models import FollowUpCase

        nv = int((await s.execute(select(func.count(FollowUpCase.id)).where(FollowUpCase.tenant_id == tid, FollowUpCase.trang_thai != "hoan_thanh",
                                                                            FollowUpCase.han < today))).scalar() or 0)
        if nv:
            out.append({"loai": "van_hanh", "muc_do": "quan_trong", "tieu_de": f"{nv} nhiệm vụ chỉ đạo quá hạn", "lien_ket": "/canh-bao"})
    groups = {g for g, q in user.permissions.items() if "nhap" in q}
    if groups and "man_hinh_tv" not in user.roles:
        from app.compliance.service import reminders

        rem = await reminders(s, tid, today, groups)
        qh = sum(1 for r in rem if r["muc"] == "qua_han")
        if qh:
            out.append({"loai": "van_hanh", "muc_do": "quan_trong", "tieu_de": f"{qh} kỳ số liệu quá hạn nộp", "lien_ket": "/nhap-lieu?tab=tuan-thu"})
    return out


@router.get("/bang-tin")
async def ticker(s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> dict:
    tid = s.info["tenant_id"]
    today = date.today()
    tv = "man_hinh_tv" in user.roles
    q = select(ThongBao).where(ThongBao.tenant_id == tid, ThongBao.tu_ngay <= today,
                               or_(ThongBao.den_ngay.is_(None), ThongBao.den_ngay >= today))
    if tv:
        q = q.where(ThongBao.hien_tren_tv.is_(True))
    rows = [t for t in (await s.execute(q)).scalars() if not t.doi_tuong or set(t.doi_tuong) & user.roles or tv and "man_hinh_tv" in t.doi_tuong]
    rows.sort(key=lambda t: (not t.ghim, MUC.get(t.muc_do, 2), -t.tu_ngay.toordinal(), -t.id))
    items = [{"loai": "thong_bao", "id": t.id, "tieu_de": t.tieu_de, "noi_dung": t.noi_dung, "lien_ket": t.lien_ket, "muc_do": t.muc_do,
              "tu_ngay": t.tu_ngay, "ghim": t.ghim} for t in rows]
    auto = await _auto(s, user, tid, today)
    from datetime import UTC, datetime, timedelta

    from app.tin_ngoai.models import TinNgoai

    tin = list((await s.execute(select(TinNgoai).where(TinNgoai.tenant_id == tid, or_(TinNgoai.ngay_dang.is_(None),
                                                                                    TinNgoai.ngay_dang >= datetime.now(UTC) - timedelta(days=7)))
                                .order_by(TinNgoai.ngay_dang.desc().nullslast(), TinNgoai.id.desc()).limit(6))).scalars())
    ngoai = [{"loai": "tin_ngoai", "tieu_de": x.tieu_de, "nguon": x.ten_nguon, "lien_ket": x.lien_ket, "muc_do": "thuong", "ngay_dang": x.ngay_dang} for x in tin]
    t = await s.get(Tenant, tid)
    links = (t.config or {}).get("lien_ket") or default_links(t)
    can_post = user.can("duyet", "canh_bao") or user.can("duyet", "quan_tri")
    return jsonable({"muc": [*[i for i in items if i["ghim"] or i["muc_do"] == "khan"], *auto, *[i for i in items if not (i["ghim"] or i["muc_do"] == "khan")], *ngoai],
                     "lien_ket": [] if tv else links, "co_quyen_dang": can_post and not tv})
