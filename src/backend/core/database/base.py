from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Float, Numeric, String, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase, MappedAsDataclass):
    pass


class PrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(default=False, server_default="false", index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None

    @classmethod
    def __declare_last__(cls) -> None:
        event.listen(cls, "load", cls._load_listener)

    @staticmethod
    def _load_listener(target, context) -> None:
        pass


class TenantAwareMixin:
    hospital_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )


class CurrencyMixin:
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False,
        default=Decimal("0.00"),
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="ZMW",
        server_default="ZMW",
    )


class BaseModel(Base, PrimaryKeyMixin, TimestampMixin):
    __abstract__ = True


class BaseSoftDeleteModel(Base, PrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __abstract__ = True


class BaseTenantModel(Base, PrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, TenantAwareMixin):
    __abstract__ = True


class BaseCurrencyModel(Base, PrimaryKeyMixin, TimestampMixin, CurrencyMixin):
    __abstract__ = True


class BaseFullModel(Base, PrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, TenantAwareMixin, CurrencyMixin):
    __abstract__ = True


class HealthMetricModel(Base, PrimaryKeyMixin, TimestampMixin, TenantAwareMixin):
    __abstract__ = True

    metric_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_unit: Mapped[str] = mapped_column(String(50), nullable=True)
