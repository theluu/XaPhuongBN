from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.models import LOP, CapitalPlan, Disbursement, Milestone, Project, ProjectIssue

MOC = {"dau_thau": "Đấu thầu", "khoi_cong": "Khởi công", "thi_cong": "Thi công", "nghiem_thu": "Nghiệm thu", "ban_giao": "Bàn giao"}


def _pct(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None or not b:
        return None
    return (a * 100 / b).quantize(Decimal("0.1"), ROUND_HALF_UP)


async def _plan(s: AsyncSession, pid: int, ky: str) -> Decimal | None:
    return (await s.execute(select(CapitalPlan.ke_hoach_von).where(CapitalPlan.project_id == pid, CapitalPlan.ky == ky))).scalar()


async def _disb(s: AsyncSession, pid: int, ky: str) -> Disbursement | None:
    """Số giải ngân lũy kế mới nhất đến hết kỳ (cùng năm)."""
    return (await s.execute(select(Disbursement).where(
        Disbursement.project_id == pid, Disbursement.ky <= ky, Disbursement.ky >= ky[:4]
    ).order_by(Disbursement.ky.desc(), Disbursement.id.desc()))).scalars().first()


async def project_row(s: AsyncSession, p: Project, ky: str) -> dict:
    kh_nam = await _plan(s, p.id, ky[:4])
    lich = await _plan(s, p.id, ky)
    d = await _disb(s, p.id, ky)
    lk = d.luy_ke if d else None
    return {
        "id": p.id, "ma_du_an": p.ma_du_an, "ten": p.ten, "lop": p.lop, "lop_ten": LOP[p.lop], "chu_dau_tu": p.chu_dau_tu,
        "nguon_von": p.nguon_von, "tong_muc_dt": p.tong_muc_dt, "dia_diem": p.dia_diem, "trang_thai": p.trang_thai,
        "ngay_ht_ke_hoach": p.ngay_ht_ke_hoach, "ke_hoach_von_nam": kh_nam, "lich_von_ky": lich,
        "giai_ngan_luy_ke": lk, "ty_le_giai_ngan_pct": _pct(lk, kh_nam),
        "khoi_luong_pct": d.khoi_luong_pct if d else None, "trang_thai_xac_nhan": d.trang_thai_xac_nhan if d else None,
        "cham_giai_ngan": lich is not None and lk is not None and lk < lich,
        "lat": p.lat, "lng": p.lng, "is_sample": p.is_sample,
    }


async def list_projects(s: AsyncSession, tenant_id: int, ky: str, lop: int | None = None) -> list[dict]:
    q = select(Project).where(Project.tenant_id == tenant_id).order_by(Project.lop, Project.ma_du_an)
    if lop:
        q = q.where(Project.lop == lop)
    return [await project_row(s, p, ky) for p in (await s.execute(q)).scalars()]


async def summary(s: AsyncSession, tenant_id: int, ky: str) -> dict:
    rows = await list_projects(s, tenant_id, ky)
    theo_lop = {}
    for lop in (1, 2, 3):
        rs = [r for r in rows if r["lop"] == lop]
        kh = [r["ke_hoach_von_nam"] for r in rs if r["ke_hoach_von_nam"] is not None]
        gn = [r["giai_ngan_luy_ke"] for r in rs if r["giai_ngan_luy_ke"] is not None]
        theo_lop[str(lop)] = {
            "ten": LOP[lop], "so_du_an": len(rs), "ke_hoach_von": sum(kh, Decimal(0)) if kh else None,
            "giai_ngan": sum(gn, Decimal(0)) if gn else None, "so_cham": sum(r["cham_giai_ngan"] for r in rs),
            "thieu_so_lieu": sum(r["giai_ngan_luy_ke"] is None for r in rs), "tinh_vao_ty_le": lop == 1,
        }
    l1 = theo_lop["1"]
    return {"ky": ky, "ty_le_giai_ngan_ns_phuong": _pct(l1["giai_ngan"], l1["ke_hoach_von"]), "theo_lop": theo_lop,
            "is_sample": any(r["is_sample"] for r in rows)}


async def slow_disbursement(s: AsyncSession, tenant_id: int, ky: str) -> list[dict]:
    """Dự án giải ngân chậm so với lịch vốn lũy kế đã duyệt của kỳ (DT II.4)."""
    out = []
    for r in await list_projects(s, tenant_id, ky):
        if r["cham_giai_ngan"]:
            out.append({"project_id": r["id"], "ma_du_an": r["ma_du_an"], "ten": r["ten"], "lich_von_ky": r["lich_von_ky"], "giai_ngan_luy_ke": r["giai_ngan_luy_ke"]})
    return out


async def overdue_milestones(s: AsyncSession, tenant_id: int, today: date) -> list[dict]:
    rows = (await s.execute(select(Milestone, Project).join(Project, Project.id == Milestone.project_id).where(
        Milestone.tenant_id == tenant_id, Milestone.ngay_thuc_te.is_(None), Milestone.han < today,
    ).order_by(Milestone.han))).all()
    return [{"project_id": p.id, "ma_du_an": p.ma_du_an, "ten": p.ten, "loai": m.loai, "loai_ten": MOC.get(m.loai, m.loai),
             "han": m.han, "so_ngay_tre": (today - m.han).days} for m, p in rows]


async def detail(s: AsyncSession, p: Project, ky: str) -> dict:
    row = await project_row(s, p, ky)
    ms = (await s.execute(select(Milestone).where(Milestone.project_id == p.id).order_by(Milestone.han))).scalars()
    iss = (await s.execute(select(ProjectIssue).where(ProjectIssue.project_id == p.id).order_by(ProjectIssue.id))).scalars()
    hist = (await s.execute(select(Disbursement).where(Disbursement.project_id == p.id).order_by(Disbursement.ky))).scalars()
    plans = (await s.execute(select(CapitalPlan).where(CapitalPlan.project_id == p.id, CapitalPlan.ky != str(p.id)).order_by(CapitalPlan.ky))).scalars()
    today = date.today()
    return {
        **row, "don_vi_phu_trach": p.don_vi_phu_trach,
        "moc": [{"loai": m.loai, "loai_ten": MOC.get(m.loai, m.loai), "han": m.han, "ngay_thuc_te": m.ngay_thuc_te,
                 "qua_han": m.ngay_thuc_te is None and m.han < today} for m in ms],
        "vuong_mac": [{"id": i.id, "noi_dung": i.noi_dung, "nguyen_nhan": i.nguyen_nhan, "trach_nhiem": i.trach_nhiem,
                       "huong_xu_ly": i.huong_xu_ly, "can_quyet_dinh": i.can_quyet_dinh, "han": i.han, "trang_thai": i.trang_thai,
                       "ho_so_keys": i.ho_so_keys} for i in iss],
        "giai_ngan_theo_ky": [{"ky": h.ky, "luy_ke": h.luy_ke, "khoi_luong_pct": h.khoi_luong_pct} for h in hist],
        "lich_von": [{"ky": c.ky, "ke_hoach_von": c.ke_hoach_von} for c in plans if len(c.ky) > 4],
    }
