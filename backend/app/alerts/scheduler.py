"""Chạy quy tắc cảnh báo hằng đêm và ngay sau khi số liệu được xác nhận."""
import logging

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
            await run_rules(s, tenant_id)
            await s.commit()
    except Exception:  # noqa: BLE001
        log.exception("Lỗi chạy quy tắc cảnh báo cho đơn vị %s", tenant_id)


async def run_all() -> None:
    async with admin_sessionmaker()() as s:
        ids = list((await s.execute(select(Tenant.id).where(Tenant.cap.in_(["xa", "phuong"]), Tenant.trang_thai == "hoat_dong"))).scalars())
    for tid in ids:
        await run_tenant(tid)


@on("value_confirmed")
async def _on_confirm(tenant_id: int, **_: object) -> None:
    await run_tenant(tenant_id)


def start() -> AsyncIOScheduler:
    sch = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
    sch.add_job(run_all, "cron", hour=1, minute=0, id="canh_bao_hang_dem", replace_existing=True)
    sch.start()
    return sch
