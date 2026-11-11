"""Dân cư tổng hợp minh họa ~52 nghìn người, 12 TDP, biến động tháng 01–10/2026 (chỉ số tổng hợp, không có cá nhân)."""
from decimal import Decimal

from sqlalchemy import select

from app.platform.models import ResidentialGroup
from app.population.models import PopulationStat
from app.population.service import NHOM_TUOI

# tỷ trọng từng nhóm tuổi (phường đô thị trẻ, đang già hóa)
TY_TRONG = [7.4, 7.9, 7.6, 6.8, 7.1, 8.6, 9.0, 8.2, 7.3, 6.4, 5.6, 4.7, 4.0, 3.1, 2.2, 1.6, 1.3, 0.9]
TDP_TY_TRONG = [9.8, 8.7, 10.6, 7.9, 8.4, 6.1, 9.2, 7.6, 8.8, 7.4, 8.1, 7.4]


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    tdps = list((await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == tenant_id).order_by(ResidentialGroup.ma_tdp))).scalars())
    dan_so = 51_200
    for m in range(1, 11):
        ky = f"2026-{m:02d}"
        sinh, tu, den, di = 52 + m % 7, 19 + m % 4, 96 + (m * 7) % 30, 61 + (m * 5) % 18
        dan_so += sinh - tu + den - di
        add = lambda cs, v, gioi="", nt="", tdp=None: s.add(PopulationStat(  # noqa: E731
            tenant_id=tenant_id, ky=ky, tdp_id=tdp, chi_so=cs, gioi=gioi, nhom_tuoi=nt, gia_tri=Decimal(int(v)), is_sample=True))
        for nt, w in zip(NHOM_TUOI, TY_TRONG):
            group = dan_so * w / sum(TY_TRONG)
            nam_share = 0.515 if nt in ("0-4", "5-9", "10-14", "15-19") else (0.38 if nt in ("80-84", "85+") else 0.495)
            add("nhan_khau", round(group * nam_share), "nam", nt)
            add("nhan_khau", round(group * (1 - nam_share)), "nu", nt)
        add("so_ho", round(dan_so / 3.55))
        for k, v in (("sinh", sinh), ("tu", tu), ("chuyen_den", den), ("chuyen_di", di)):
            add(k, v)
        for g, w in zip(tdps, TDP_TY_TRONG):
            add("nhan_khau", round(dan_so * w / 100), tdp=g.id)
