import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.db import Base, import_models

import_models()
target_metadata = Base.metadata


def do_run(conn) -> None:  # noqa: ANN001
    context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def main() -> None:
    eng = create_async_engine(os.environ["ADMIN_DATABASE_URL"])
    async with eng.connect() as conn:
        await conn.run_sync(do_run)
        await conn.commit()
    await eng.dispose()


asyncio.run(main())
