from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.models import Alert, AlertRule
from app.alerts.rules import DATA_TYPES, QUALITY, RULES, Ctx


def last_finished_month(today: date) -> str:
    y, m = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    return f"{y}-{m:02d}"


async def run_rules(s: AsyncSession, tenant_id: int, today: date | None = None, ky: str | None = None) -> list[Alert]:
    """Chạy toàn bộ quy tắc cho một đơn vị. Idempotent theo dedupe_key; cảnh báo 'mới' không còn điều kiện → hết hiệu lực."""
    today = today or date.today()
    ky = ky or last_finished_month(today)
    cfg = {r.ma: r for r in (await s.execute(select(AlertRule).where(AlertRule.tenant_id == tenant_id))).scalars()}
    existing = {a.dedupe_key: a for a in (await s.execute(select(Alert).where(Alert.tenant_id == tenant_id))).scalars()}
    x = Ctx(s, tenant_id, today, ky)
    seen: set[str] = set()
    out: list[Alert] = []
    now = datetime.now(UTC)
    for ma, r in RULES.items():
        if ma in cfg and not cfg[ma].bat:
            continue
        for c in await r.fn(x):
            key = f"{ma}:{c.ref}"
            seen.add(key)
            a = existing.get(key)
            if a is None:
                a = Alert(tenant_id=tenant_id, rule_ma=ma, dedupe_key=key, doi_tuong_ref=c.ref)
                s.add(a)
                existing[key] = a
            elif a.trang_thai == "het_hieu_luc":
                a.trang_thai = "moi"
            a.loai, a.nhom, a.muc_do, a.tieu_de, a.mo_ta, a.link, a.ky = r.loai, c.nhom, c.muc_do, c.tieu_de, c.mo_ta, c.link, ky
            a.ghi_chu_chat_luong = QUALITY if r.loai in DATA_TYPES else None
            a.lan_cuoi_kiem_tra = now
            out.append(a)
    for key, a in existing.items():
        if key not in seen and a.trang_thai == "moi":
            a.trang_thai = "het_hieu_luc"
    await s.flush()
    return out
