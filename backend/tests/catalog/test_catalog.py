from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.catalog.cycles import DEFAULT_CYCLES
from app.catalog.models import Indicator, IndicatorPlan, Program, Scenario
from app.catalog.packs import apply_pack
from app.catalog.schemas import IndicatorIn
from app.catalog.service import program_progress
from app.core.db import admin_sessionmaker
from tests.factories import make_tenant

BASE = dict(
    ma_chi_tieu="X-01", ten="Chỉ tiêu thử", dinh_nghia="Định nghĩa", cong_thuc="A/B*100", pham_vi_dia_ban="Toàn phường",
    nhom="ktxh", phan_he="ktxh", don_vi_do="%", chieu="tang_tot", nguon_mac_dinh="UBND phường",
    don_vi_chu_quan="Văn phòng", ky_cap_nhat="thang",
)


def test_indicator_metadata_required_fields():
    IndicatorIn(**BASE)
    for missing in ["dinh_nghia", "cong_thuc", "pham_vi_dia_ban", "don_vi_do", "nguon_mac_dinh", "don_vi_chu_quan", "ky_cap_nhat"]:
        data = {k: v for k, v in BASE.items() if k != missing}
        with pytest.raises(ValidationError):
            IndicatorIn(**data)
    with pytest.raises(ValidationError):
        IndicatorIn(**{**BASE, "dinh_nghia": "  "})
    with pytest.raises(ValidationError):
        IndicatorIn(**{**BASE, "chieu": "len_xuong"})


def test_dat_nguong_needs_operator_and_target():
    with pytest.raises(ValidationError):
        IndicatorIn(**{**BASE, "chieu": "dat_nguong"})
    IndicatorIn(**{**BASE, "chieu": "dat_nguong", "nguong_toan_tu": ">=", "muc_tieu": Decimal("99.8")})
    IndicatorIn(**{**BASE, "chieu": "dat_nguong", "muc_tieu_khoang": [Decimal(15), Decimal(18)]})


async def test_plan_unique_per_period():
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        ind = Indicator(tenant_id=t, **IndicatorIn(**BASE).model_dump())
        s.add(ind)
        await s.flush()
        s.add(IndicatorPlan(indicator_id=ind.id, tenant_id=t, nam=2026, ky="2026-Q3", gia_tri_ke_hoach=Decimal(40)))
        await s.commit()
        s.add(IndicatorPlan(indicator_id=ind.id, tenant_id=t, nam=2026, ky="2026-Q3", gia_tri_ke_hoach=Decimal(41)))
        with pytest.raises(Exception):
            await s.commit()


PACK = {
    "ma": "pack_thu", "ten": "Gói thử", "phien_ban": 1,
    "indicators": [
        {**BASE, "ma_chi_tieu": "P-01", "ten": "Chỉ tiêu P1"},
        {**BASE, "ma_chi_tieu": "P-02", "ten": "Chỉ tiêu P2"},
    ],
    "programs": [{"ma": "NV-1", "ten": "Nhiệm vụ 1", "mo_ta": "", "don_vi_chu_tri": "UBND", "indicator_mas": ["P-01", "P-02"]}],
    "scenarios": [{"ma": "KB-01", "ten": "Kịch bản 1", "la_bo_sung": False, "indicator_mas": ["P-01"],
                   "rule_codes": ["CT_CHAM_KH"], "layout": {"khu": ["the_chi_so", "xu_huong"]}}],
}


async def test_apply_pack_then_upgrade_keeps_custom():
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        await apply_pack(s, t, PACK)
        await s.commit()
        p1 = (await s.execute(select(Indicator).where(Indicator.tenant_id == t, Indicator.ma_chi_tieu == "P-01"))).scalar_one()
        p1.ten = "Tên phường tự sửa"
        p1.da_chinh_sua = True
        await s.commit()
        v2 = {**PACK, "phien_ban": 2, "indicators": [
            {**BASE, "ma_chi_tieu": "P-01", "ten": "Tên gói v2"},
            {**BASE, "ma_chi_tieu": "P-02", "ten": "P2 v2"},
            {**BASE, "ma_chi_tieu": "P-03", "ten": "Mới v2"},
        ]}
        await apply_pack(s, t, v2)
        await s.commit()
        rows = {i.ma_chi_tieu: i for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == t))).scalars()}
    assert rows["P-01"].ten == "Tên phường tự sửa"
    assert rows["P-02"].ten == "P2 v2" and rows["P-02"].pack_phien_ban == 2
    assert "P-03" in rows


async def test_scenario_bundles_indicators_rules_layout():
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        await apply_pack(s, t, PACK)
        await s.commit()
        sc = (await s.execute(select(Scenario).where(Scenario.tenant_id == t, Scenario.ma == "KB-01"))).scalar_one()
        p1 = (await s.execute(select(Indicator.id).where(Indicator.tenant_id == t, Indicator.ma_chi_tieu == "P-01"))).scalar_one()
    assert sc.indicator_ids == [p1]
    assert sc.rule_codes == ["CT_CHAM_KH"]
    assert sc.layout == {"khu": ["the_chi_so", "xu_huong"]}


async def test_program_progress_rollup():
    t = await make_tenant()
    async with admin_sessionmaker()() as s:
        await apply_pack(s, t, PACK)
        await s.commit()
        prog = (await s.execute(select(Program).where(Program.tenant_id == t))).scalar_one()
        ids = prog.indicator_ids
    r = program_progress(prog, {ids[0]: "dat", ids[1]: "chua_du_du_lieu"})
    assert r == {"tong": 2, "dat": 1, "nguy_co": 0, "chua_du_du_lieu": 1, "ty_le_dat_pct": Decimal("50.0")}
    r = program_progress(prog, {ids[0]: "chua_du_du_lieu", ids[1]: "chua_du_du_lieu"})
    assert r["ty_le_dat_pct"] is None  # chưa đủ dữ liệu thì không kết luận 0%


def test_update_cycle_defaults_from_dt_table():
    assert DEFAULT_CYCLES["ktxh"] == {"ky": ["thang", "quy", "nam"], "dieu_kien": "Theo kỳ báo cáo chính thức; phường ký xác nhận", "can_xac_nhan": True}
    assert DEFAULT_CYCLES["dan_cu"]["ky"] == ["thang"]
    assert DEFAULT_CYCLES["ngan_sach"]["ky"] == ["tuan", "thang"]
    assert DEFAULT_CYCLES["dau_tu_cong"]["ky"] == ["tuan"]
    assert DEFAULT_CYCLES["cong_trinh"]["can_minh_chung"] is True
    assert DEFAULT_CYCLES["tthc_pakn"]["ky"] == ["api", "ky_bao_cao"]
    assert DEFAULT_CYCLES["gd_yt_mt"]["ky"] == ["thang", "quy"]
