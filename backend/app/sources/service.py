import inspect
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.models import Tenant
from app.sources import builtin  # noqa: F401  (đăng ký connector dựng sẵn)
from app.sources.builtin import KHO_DL_DAN_CU_ENDPOINTS
from app.sources.models import DataSource, SyncRun
from app.sources.registry import CONNECTORS, PII_KEYS, SINKS

PHAN_HE = ["ktxh", "dan_cu", "ngan_sach", "dau_tu_cong", "cong_trinh", "tthc_pakn", "gd_yt_mt"]


async def ensure_default_sources(s: AsyncSession) -> None:
    defaults = [
        DataSource(
            tenant_id=None, ma="KHO_DL_DAN_CU", ten="Kho dữ liệu dùng chung — API dân cư", loai="api",
            co_quan_cung_cap="Công an thành phố / Kho dữ liệu số dùng chung", nhom_du_lieu="dan_cu",
            config={"connector": "kho_dl_dan_cu", "sink": "population", "mock": True},
            endpoints=[{"ma": m, "ten": t, "ket_noi": True, "tra_du_lieu": d} for m, t, d in KHO_DL_DAN_CU_ENDPOINTS],
            trang_thai="hoat_dong_mot_phan", phap_ly_chia_se="cho_phep_mot_phan",
        ),
        DataSource(
            tenant_id=None, ma="PAKN_API", ten="Hệ thống phản ánh kiến nghị (API về IOC thành phố)", loai="api",
            co_quan_cung_cap="Hệ thống phản ánh kiến nghị", nhom_du_lieu="tthc_pakn",
            config={"connector": "pakn_api", "sink": "pakn", "mock": True}, endpoints=[{"ma": "phan_anh", "ten": "Phản ánh", "ket_noi": True, "tra_du_lieu": True}],
            trang_thai="hoat_dong", phap_ly_chia_se="da_cho_phep",
        ),
        DataSource(
            tenant_id=None, ma="DVCQG_TTHC", ten="Cổng DVCQG — hồ sơ TTHC (gián đoạn từ 01/6/2026, nhập biểu mẫu động)",
            loai="api", co_quan_cung_cap="Văn phòng UBND thành phố", nhom_du_lieu="tthc_pakn",
            config={"ghi_chu": "Tạm thời nhập trực tiếp qua biểu mẫu động"}, endpoints=[], trang_thai="loi",
            phap_ly_chia_se="da_cho_phep",
        ),
    ]
    for d in defaults:
        if (await s.execute(select(DataSource.id).where(DataSource.ma == d.ma))).scalar() is None:
            s.add(d)
    await s.flush()


def source_out(src: DataSource) -> dict:
    eps = src.endpoints or []
    return {
        "id": src.id, "ma": src.ma, "ten": src.ten, "loai": src.loai, "co_quan_cung_cap": src.co_quan_cung_cap,
        "nhom_du_lieu": src.nhom_du_lieu, "trang_thai": src.trang_thai, "phap_ly_chia_se": src.phap_ly_chia_se,
        "dung_chung": src.tenant_id is None, "lan_dong_bo_cuoi": src.lan_dong_bo_cuoi,
        "tong_api": len(eps), "so_api_ket_noi": sum(1 for e in eps if e.get("ket_noi")),
        "so_api_tra_du_lieu": sum(1 for e in eps if e.get("tra_du_lieu")),
        "endpoints": eps, "ghi_chu": src.config.get("ghi_chu", ""),
    }


def _derive_status(src: DataSource) -> str:
    eps = src.endpoints or []
    if not eps:
        return "hoat_dong"
    n = sum(1 for e in eps if e.get("tra_du_lieu"))
    return "hoat_dong" if n == len(eps) else ("khong_tra_du_lieu" if n == 0 else "hoat_dong_mot_phan")


async def run_sync(s: AsyncSession, source_id: int, tenant_ids: list[int], ky: str) -> SyncRun:
    src = await s.get(DataSource, source_id)
    if src is None:
        raise ValueError("Không có nguồn dữ liệu")
    run = SyncRun(source_id=src.id, tenant_ids=tenant_ids, ky=ky)
    s.add(run)
    notes: list[str] = []
    total = 0
    try:
        fetch = CONNECTORS[src.config["connector"]]
        put = SINKS[src.config.get("sink", "noop")]
        for tid in tenant_ids:
            tenant = await s.get(Tenant, tid)
            records = await fetch(src, tenant, ky)
            clean = [r for r in records if not (PII_KEYS & set(r))]
            if len(clean) != len(records):
                notes.append(f"{len(records) - len(clean)} bản ghi bị loại vì chứa thông tin định danh cá nhân")
            n = put(s, tid, clean)
            total += await n if inspect.isawaitable(n) else n
        src.trang_thai = _derive_status(src)
    except Exception as e:  # noqa: BLE001
        src.trang_thai = "loi"
        notes.append(f"Lỗi đồng bộ: {e}")
    run.so_ban_ghi = total
    run.loi = "; ".join(notes)
    run.ket_thuc = datetime.now(UTC)
    src.lan_dong_bo_cuoi = run.ket_thuc
    await s.commit()
    return run


ACTIVE = {"hoat_dong", "hoat_dong_mot_phan"}


async def module_status(s: AsyncSession, tenant_id: int) -> dict[str, str]:
    """Trạng thái từng phân hệ: tat | bat | dang_ket_noi (DT V.3: nhóm chưa đáp ứng đánh dấu 'đang kết nối')."""
    tenant = await s.get(Tenant, tenant_id)
    srcs = list((await s.execute(
        select(DataSource).where((DataSource.tenant_id == tenant_id) | (DataSource.tenant_id.is_(None)))
    )).scalars())
    from app.catalog.models import Indicator
    from app.indicators.models import IndicatorValue

    manual = set((await s.execute(
        select(Indicator.phan_he).join(IndicatorValue, IndicatorValue.indicator_id == Indicator.id)
        .where(IndicatorValue.tenant_id == tenant_id, IndicatorValue.trang_thai == "da_xac_nhan").distinct()
    )).scalars())
    out: dict[str, str] = {}
    for ph in PHAN_HE:
        if (tenant.modules or {}).get(ph) == "tat":
            out[ph] = "tat"
        elif ph in manual or any(x.nhom_du_lieu == ph and x.trang_thai in ACTIVE for x in srcs):
            out[ph] = "bat"
        else:
            out[ph] = "dang_ket_noi"
    return out
