"""Check existing DB schema."""
import asyncio
from sqlalchemy import text
from src.backend.database import async_session_factory


async def check():
    async with async_session_factory() as session:
        rows = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        )
        tables = [r[0] for r in rows]
        print("Tables:", tables)

        for tbl in tables:
            cols = await session.execute(
                text(
                    "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                    "WHERE table_name=:t ORDER BY ordinal_position"
                ),
                {"t": tbl},
            )
            print(f"\n{tbl}:")
            for c in cols:
                print(f"  {c[0]} ({c[1]}) nullable={c[2]}")


asyncio.run(check())
