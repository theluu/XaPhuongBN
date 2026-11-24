"""Bổ sung (không ghi đè) địa chỉ công khai + danh mục công khai cho các đơn vị demo, và công bố sẵn các kỳ minh họa nếu chưa có.

Chạy: python -m seeds.cong_khai_init
"""
import asyncio

from sqlalchemy import select

from app.auth.models import Grant, User
from app.core.db import admin_sessionmaker, import_models
from app.platform.models import Tenant
from seeds.run import _sample_cong_bo, _yaml

KEYS = ("slug", "ten_mien", "cong_khai")


async def main() -> None:
    import_models()
    from app.cong_khai.models import CongBo

    for code in ("viet_yen", "nenh"):
        spec = _yaml(f"tenants/{code}/tenant.yaml")["tenant"]
        async with admin_sessionmaker()() as s:
            t = (await s.execute(select(Tenant).where(Tenant.ma_dvhc == spec["ma_dvhc"]))).scalar()
            if t is None:
                print(f"{code}: chưa có đơn vị, bỏ qua")
                continue
            missing = {k: spec["config"][k] for k in KEYS if k in spec["config"] and k not in (t.config or {})}
            if missing:
                t.config = {**(t.config or {}), **missing}
            await s.commit()
            has = (await s.execute(select(CongBo.id).where(CongBo.tenant_id == t.id).limit(1))).scalar()
            leader = (await s.execute(select(User.id).join(Grant, Grant.user_id == User.id)
                                      .where(User.tenant_id == t.id, Grant.role == "lanh_dao").order_by(User.id).limit(1))).scalar()
            tid = t.id
        if not has:
            await _sample_cong_bo(tid, {"chutich": leader})
        print(f"{code}: bổ sung {sorted(missing)}; công bố mẫu: {'đã có' if has else 'đã tạo'}")


if __name__ == "__main__":
    asyncio.run(main())
