"""Apply migrations with the same asyncpg driver used by the deployed EMR."""
import asyncio
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "scripts/migration/alembic.ini"))
    config.set_main_option("script_location", str(root / "data/migrations"))
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.connect() as connection:
            def upgrade(sync_connection):
                config.attributes["connection"] = sync_connection
                command.upgrade(config, "head")
            await connection.run_sync(upgrade)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
