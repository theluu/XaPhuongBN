"""Chạy quy tắc cảnh báo hằng đêm và ngay sau khi số liệu được xác nhận."""
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.alerts.engine import run_rules
from app.core.db import admin_sessionmaker, tenant_session
from app.events import on
from app.platform.models import Tenant

log = logging.getLogger("ioc.alerts")


async def run_tenant(tenant_id: int) -> None:
    try:
        async with tenant_session([tenant_id]) as s:
            from app.alerts.models import Alert

            before = set((await s.execute(select(Alert.id).where(Alert.tenant_id == tenant_id))).scalars())
            out = await run_rules(s, tenant_id)
            await s.commit()
            new = [a for a in out if a.id not in before]
            if new:
                from datetime import date

                from app.noti.service import notify, users_with

                top = sorted(new, key=lambda a: {"cao": 0, "trung_binh": 1}.get(a.muc_do, 2))[0]
                await notify(s, tenant_id, await users_with(tenant_id, roles={"lanh_dao"}), "canh_bao",
                             f"{len(new)} cảnh báo mới" if len(new) > 1 else f"Cảnh báo mới: {top.tieu_de}",
                             top.tieu_de if len(new) > 1 else (top.mo_ta or "")[:300], "/canh-bao", "quan_trong", f"canh_bao_moi:{date.today().isoformat()}")
    except Exception:  # noqa: BLE001
        log.exception("Lỗi chạy quy tắc cảnh báo cho đơn vị %s", tenant_id)


LOCK_KEY = 7_420_001


@asynccontextmanager
async def nightly_lock():  # noqa: ANN201
    """Khóa tư vấn PostgreSQL: chỉ một tiến trình (trong nhiều worker) chạy quy tắc hằng đêm."""
    from sqlalchemy import text

    from app.core.db import engine

    async with engine("admin").connect() as c:
        got = bool((await c.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": LOCK_KEY})).scalar())
        try:
            yield got
        finally:
            if got:
                await c.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LOCK_KEY})


async def run_all() -> None:
    async with nightly_lock() as got:
        if not got:
            return
        async with admin_sessionmaker()() as s:
            ids = list((await s.execute(select(Tenant.id).where(Tenant.cap.in_(["xa", "phuong"]), Tenant.trang_thai == "hoat_dong"))).scalars())
        for tid in ids:
            await run_tenant(tid)


@on("value_confirmed")
async def _on_confirm(tenant_id: int, **_: object) -> None:
    await run_tenant(tenant_id)


FEED_LOCK = 7_420_002


async def _feeds() -> None:
    """Lấy tin từ nguồn RSS/Atom mỗi 30 phút (một tiến trình nhờ khóa tư vấn)."""
    from sqlalchemy import text

    from app.core.db import engine
    from app.tin_ngoai.service import refresh_all

    async with engine("admin").connect() as c:
        if not (await c.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": FEED_LOCK})).scalar():
            return
        try:
            await refresh_all()
        except Exception:  # noqa: BLE001
            log.exception("Lỗi lấy nguồn tin")
        finally:
            await c.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": FEED_LOCK})


def start() -> AsyncIOScheduler:
    sch = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
    sch.add_job(run_all, "cron", hour=1, minute=0, id="canh_bao_hang_dem", replace_existing=True)
    sch.add_job(_feeds, "interval", minutes=30, id="nguon_tin", replace_existing=True)
    sch.start()
    return sch
