"""Verify seed data in DB."""
import asyncio

from sqlalchemy import text
from src.backend.database import async_session_factory

TABLES = [
    "hospitals", "patients", "encounters", "diagnoses",
    "medications", "allergies", "problem_list",
    "clinical_notes", "family_histories", "social_histories",
    "orders", "results", "immunizations",
    "outbreak_alerts", "surveillance_reports", "disease_cases",
    "appointments", "teleconsultations",
]

async def check():
    async with async_session_factory() as session:
        for tbl in TABLES:
            try:
                row = await session.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                count = row.scalar()
                print(f"{tbl}: {count}")
            except Exception as e:
                print(f"{tbl}: ERROR - {e}")

asyncio.run(check())
