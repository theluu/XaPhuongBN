from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import tenant_db
from app.core.db import admin_sessionmaker
from app.platform.models import Tenant
from app.sources.service import module_status

router = APIRouter(prefix="/api", tags=["don-vi"])
CAP = {"phuong": "phường", "xa": "xã", "tinh": "tỉnh", "nen_tang": "nền tảng"}


def agency_name(t: Tenant) -> list[str]:
    cfg = t.config or {}
    if cfg.get("ten_co_quan"):
        return list(cfg["ten_co_quan"])
    if t.cap in ("phuong", "xa"):
        return [f"ĐẢNG ỦY – UBND {t.ten.upper()}", f"Hệ thống điều hành số {CAP[t.cap]}"]
    return [t.ten.upper(), "Hệ thống điều hành số"]


@router.get("/tenant")
async def current_tenant(s: AsyncSession = Depends(tenant_db)) -> dict:
    tid = s.info["tenant_id"]
    async with admin_sessionmaker()() as adm:
        t = await adm.get(Tenant, tid)
        modules = await module_status(adm, tid)
    cfg = t.config or {}
    return {
        "id": t.id, "ma_dvhc": t.ma_dvhc, "ten": t.ten, "cap": t.cap, "ten_co_quan": agency_name(t),
        "logo_url": f"/api/files/{t.logo_key}" if t.logo_key else None,
        "ban_do": cfg.get("ban_do"), "cho_phep_theo_tdp": bool(cfg.get("cho_phep_theo_tdp")), "modules": modules,
    }


@router.get("/sample-flag")
async def sample_flag(s: AsyncSession = Depends(tenant_db)) -> dict:
    """Đơn vị còn dữ liệu minh họa → giao diện hiện dải cảnh báo (DT V.3: không dùng số giả lập làm kết quả thực tế)."""
    from sqlalchemy import text

    from app.core.db import Base, import_models

    import_models()
    for table in Base.metadata.sorted_tables:
        if "is_sample" in table.c and "tenant_id" in table.c:
            hit = (await s.execute(text(f'SELECT 1 FROM "{table.name}" WHERE tenant_id = :t AND is_sample LIMIT 1'),
                                   {"t": s.info["tenant_id"]})).first()
            if hit:
                return {"co_du_lieu_minh_hoa": True}
    return {"co_du_lieu_minh_hoa": False}
