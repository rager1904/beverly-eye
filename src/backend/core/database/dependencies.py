from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncSessionTransaction,
    async_sessionmaker,
    create_async_engine,
)

from src.backend.core.config.settings import settings

hospital_id_context: ContextVar[Optional[uuid.UUID]] = ContextVar("hospital_id", default=None)


engine = create_async_engine(
    settings.database_url,
    pool_size=settings.POSTGRES_POOL_SIZE,
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
    pool_recycle=settings.POSTGRES_POOL_RECYCLE,
    echo=settings.POSTGRES_ECHO,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class TenantAwareSession(AsyncSession):
    async def execute(self, statement, params=None, *, execution_options=None):
        hospital_id = hospital_id_context.get()
        if hospital_id is not None and hasattr(statement, "whereclause"):
            from sqlalchemy import and_
            from sqlalchemy.sql import visitors
            from sqlalchemy.orm import Query

            if isinstance(statement, Query):
                entity = statement.column_descriptions[0].get("type")
                if entity and hasattr(entity, "hospital_id"):
                    statement = statement.filter(entity.hospital_id == hospital_id)
        return await super().execute(statement, params, execution_options=execution_options)


tenant_session_factory = async_sessionmaker(
    bind=engine,
    class_=TenantAwareSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_tenant() -> AsyncGenerator[TenantAwareSession, None]:
    async with tenant_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def set_hospital_id(hospital_id: uuid.UUID) -> None:
    hospital_id_context.set(hospital_id)


def get_hospital_id() -> Optional[uuid.UUID]:
    return hospital_id_context.get()


def reset_hospital_id() -> None:
    hospital_id_context.set(None)


async def check_database_health() -> dict:
    result = {
        "status": "unhealthy",
        "latency_ms": None,
        "pool_size": None,
        "active_connections": None,
    }
    try:
        import time

        start = time.perf_counter()
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        elapsed = (time.perf_counter() - start) * 1000
        result["status"] = "healthy"
        result["latency_ms"] = round(elapsed, 2)
        result["pool_size"] = engine.pool.size()
        result["active_connections"] = engine.pool.checkedin()
    except Exception as e:
        result["status"] = "unhealthy"
        result["error"] = str(e)
    return result


class TransactionManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._transaction: Optional[AsyncSessionTransaction] = None

    async def __aenter__(self) -> AsyncSession:
        self._transaction = await self.session.begin()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self._transaction.rollback()
        else:
            try:
                await self._transaction.commit()
            except Exception:
                await self._transaction.rollback()
                raise
        await self.session.close()
