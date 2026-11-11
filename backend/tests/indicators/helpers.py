from datetime import UTC, datetime
from decimal import Decimal

from app.catalog.models import Indicator, IndicatorPlan
from app.catalog.schemas import IndicatorIn
from app.core.db import admin_sessionmaker
from app.indicators.models import IndicatorValue
from tests.factories import uid

CHOT = datetime(2026, 10, 31, tzinfo=UTC)


async def make_indicator(tenant_id: int, **kw) -> int:
    base = dict(
        ma_chi_tieu=uid("CT"), ten="Chỉ tiêu thử", dinh_nghia="Định nghĩa", cong_thuc="A/B", pham_vi_dia_ban="Toàn phường",
        nhom="ktxh", phan_he="ktxh", don_vi_do="%", chieu="tang_tot", nguon_mac_dinh="UBND phường",
        don_vi_chu_quan="Văn phòng", ky_cap_nhat="thang",
    )
    base.update(kw)
    data = IndicatorIn(**base).model_dump()
    async with admin_sessionmaker()() as s:
        i = Indicator(tenant_id=tenant_id, **data)
        s.add(i)
        await s.commit()
        return i.id


async def add_plan(tenant_id: int, indicator_id: int, ky: str, v) -> None:  # noqa: ANN001
    async with admin_sessionmaker()() as s:
        s.add(IndicatorPlan(indicator_id=indicator_id, tenant_id=tenant_id, nam=int(ky[:4]), ky=ky, gia_tri_ke_hoach=Decimal(str(v))))
        await s.commit()


async def add_value(tenant_id: int, indicator_id: int, ky: str, v, trang_thai="da_xac_nhan", nguon_loai="phuong",  # noqa: ANN001
                    version=1, du_bao=None, is_sample=False, nguoi_nhap_id=None) -> int:
    async with admin_sessionmaker()() as s:
        row = IndicatorValue(
            indicator_id=indicator_id, tenant_id=tenant_id, ky_bao_cao=ky, gia_tri=None if v is None else Decimal(str(v)),
            du_bao=None if du_bao is None else Decimal(str(du_bao)), nguon_loai=nguon_loai, nguon="Báo cáo UBND phường",
            don_vi_cung_cap="Văn phòng UBND", thoi_diem_chot=CHOT, trang_thai=trang_thai, version=version,
            nguoi_xac_nhan_ten="Chủ tịch UBND" if trang_thai == "da_xac_nhan" else None,
            ngay_xac_nhan=CHOT if trang_thai == "da_xac_nhan" else None, is_sample=is_sample, nguoi_nhap_id=nguoi_nhap_id,
        )
        s.add(row)
        await s.commit()
        return row.id
