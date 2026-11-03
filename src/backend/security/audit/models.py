from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    detail: Mapped[Optional[dict]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    hospital_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    tamper_hash: Mapped[Optional[str]] = mapped_column(String(128))
    previous_hash: Mapped[Optional[str]] = mapped_column(String(128))

    __table_args__ = (
        Index("idx_audit_logs_actor_action", "actor", "action"),
        Index("idx_audit_logs_timestamp", "timestamp"),
        Index("idx_audit_logs_resource", "resource", "resource_id"),
    )


class AccessLog(Base):
    __tablename__ = "access_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(255))
    patient_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(String(200))
    contains_phi: Mapped[bool] = mapped_column(default=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    hospital_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    consent_verified: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index("idx_access_logs_patient", "patient_id"),
        Index("idx_access_logs_phi", "contains_phi", "timestamp"),
    )


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    granted: Mapped[bool] = mapped_column(default=True)
    granted_by: Mapped[Optional[str]] = mapped_column(String(255))
    scope: Mapped[Optional[dict]] = mapped_column(JSONB)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[Optional[str]] = mapped_column(String(255))
    consent_version: Mapped[str] = mapped_column(String(20), default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_consent_patient_type", "patient_id", "consent_type"),
    )


class BreachLog(Base):
    __tablename__ = "breach_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    breach_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_patients: Mapped[Optional[list]] = mapped_column(JSONB)
    affected_records: Mapped[Optional[int]]
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reported_to_authority: Mapped[bool] = mapped_column(default=False)
    reported_to: Mapped[Optional[str]] = mapped_column(String(255))
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[str]] = mapped_column(String(255))
    hospital_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_breach_severity", "severity", "detected_at"),
    )
