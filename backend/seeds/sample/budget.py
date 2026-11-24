"""Ngân sách minh họa 2026 (đơn vị: đồng). Tình huống: tiền SDĐ chậm so tiến độ, chi môi trường vượt dự toán,
tháng 9 số API lệch báo cáo chốt, tháng 10 đang chờ đối soát."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.budget.models import BudgetLine
from app.core.periods import parse_ky
from seeds.sample import ho_so

TY = Decimal(1_000_000_000)
# lịch tiến độ thu lũy kế được duyệt (không chia đều theo tháng)
LICH = [0.06, 0.12, 0.20, 0.28, 0.36, 0.45, 0.53, 0.61, 0.70, 0.78, 0.88, 1.00]
THU = {  # nhóm: (dự toán thu trên địa bàn, phần NS phường hưởng, hệ số thực hiện so kế hoạch)
    "THUE_CTN": (120, 18, 1.04), "LE_PHI": (8, 6, 1.02), "TIEN_SDD": (250, 75, 0.72),
    "THUE_SDD_PNN": (6, 6, 0.98), "THUE_TNCN": (45, 4, 1.06), "THU_KHAC": (12, 8, 1.01),
}
CHI = {  # (nhóm, nhiệm vụ): (dự toán, hệ số lũy kế đến T10)
    ("CHI_DTPT", "NV_HATANG"): (60, 0.58), ("CHI_QLHC", "NV_BMAY"): (22, 0.81), ("CHI_QLHC", "NV_QPAN"): (2, 0.74),
    ("CHI_SN_GD", "NV_GIAODUC"): (14, 0.79), ("CHI_SN_MT", "NV_MOITRUONG"): (6, 1.07), ("CHI_DBXH", "NV_ANSINH"): (5, 0.83),
}


def _d(x: float) -> Decimal:
    return (Decimal(str(x)) * TY).quantize(Decimal(1))


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    P = ho_so.P
    for m in range(1, 11):
        ky = f"2026-{m:02d}"
        end = parse_ky(ky).ket_thuc
        chot = datetime(end.year, end.month, end.day, tzinfo=UTC) + timedelta(days=4)
        dsoat = "cho_doi_soat" if m == 10 else "da_doi_soat"
        for nhom, (db, nsp, f) in THU.items():
            f = P.he_so_thu.get(nhom, f)
            db, nsp = db * P.he_so_du_toan, nsp * P.he_so_du_toan
            for scope, dt in (("dia_ban", db), ("ns_phuong", nsp)):
                kh = dt * LICH[m - 1]
                th = kh * f
                s.add(BudgetLine(tenant_id=tenant_id, nam=2026, ky=ky, loai="thu", nhom_ma=nhom, scope=scope,
                                 du_toan=_d(dt), ke_hoach_ky=_d(kh), thuc_hien=_d(th), uoc_th=_d(dt * min(f, 1.05)) if m == 10 else None,
                                 nguon_loai="bao_cao_chot", trang_thai_doi_soat=dsoat, ngay_chot=chot, is_sample=True))
                if m == 9 and nhom == "THUE_CTN" and scope == "dia_ban":
                    s.add(BudgetLine(tenant_id=tenant_id, nam=2026, ky=ky, loai="thu", nhom_ma=nhom, scope=scope, du_toan=_d(dt),
                                     thuc_hien=_d(th * 1.034), nguon_loai="api", trang_thai_doi_soat="cho_doi_soat",
                                     ngay_chot=chot, is_sample=True))
        for (nhom, nv), (dt, f10) in CHI.items():
            dt = dt * P.he_so_du_toan
            f10 = min(f10, 0.95) if P.muoi else f10
            s.add(BudgetLine(tenant_id=tenant_id, nam=2026, ky=ky, loai="chi", nhom_ma=nhom, nhiem_vu=nv, scope="ns_phuong",
                             du_toan=_d(dt), thuc_hien=_d(dt * f10 * m / 10), nguon_loai="bao_cao_chot",
                             trang_thai_doi_soat=dsoat, ngay_chot=chot, is_sample=True))
