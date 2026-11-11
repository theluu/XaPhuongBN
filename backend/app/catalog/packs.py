"""Áp gói mẫu cho đơn vị: kế thừa rồi chỉnh; nâng cấp không ghi đè phần đơn vị đã chỉnh."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.models import Indicator, Program, Scenario
from app.catalog.schemas import IndicatorIn


async def _upsert(s: AsyncSession, model, tenant_id: int, key_field: str, key: str, values: dict, pack: dict):  # noqa: ANN001
    row = (await s.execute(select(model).where(model.tenant_id == tenant_id, getattr(model, key_field) == key))).scalar()
    if row is not None and row.da_chinh_sua:
        return row
    if row is None:
        row = model(tenant_id=tenant_id, **{key_field: key})
        s.add(row)
    for k, v in values.items():
        setattr(row, k, v)
    row.nguon_pack = pack["ma"]
    row.pack_phien_ban = pack["phien_ban"]
    return row


async def apply_pack(s: AsyncSession, tenant_id: int, pack: dict) -> None:
    ids: dict[str, int] = {}
    for raw in pack.get("indicators", []):
        data = IndicatorIn(**raw).model_dump(mode="json")
        for k in ("muc_tieu", "muc_tieu_2030", "muc_tieu_khoang"):
            if raw.get(k) is not None:
                data[k] = raw[k]  # giữ kiểu số (JSON dump đổi Decimal thành chuỗi)
        row = await _upsert(s, Indicator, tenant_id, "ma_chi_tieu", data.pop("ma_chi_tieu"), data, pack)
        await s.flush()
        ids[row.ma_chi_tieu] = row.id
    known = {i.ma_chi_tieu: i.id for i in (await s.execute(select(Indicator).where(Indicator.tenant_id == tenant_id))).scalars()}
    ids = {**known, **ids}
    for p in pack.get("programs", []):
        vals = {k: v for k, v in p.items() if k not in ("ma", "indicator_mas")}
        vals["indicator_ids"] = [ids[m] for m in p.get("indicator_mas", []) if m in ids]
        await _upsert(s, Program, tenant_id, "ma", p["ma"], vals, pack)
    for sc in pack.get("scenarios", []):
        vals = {k: v for k, v in sc.items() if k not in ("ma", "indicator_mas")}
        vals["indicator_ids"] = [ids[m] for m in sc.get("indicator_mas", []) if m in ids]
        await _upsert(s, Scenario, tenant_id, "ma", sc["ma"], vals, pack)
    await s.flush()
