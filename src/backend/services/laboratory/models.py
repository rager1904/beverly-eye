from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, TenantMixin


class SpecimenType(str, enum.Enum):
    blood = "blood"
    urine = "urine"
    stool = "stool"
    sputum = "sputum"
    swab = "swab"
    tissue = "tissue"
    cs_fluid = "cs_fluid"
    pleural_fluid = "pleural_fluid"
    ascitic_fluid = "ascitic_fluid"
    bone_marrow = "bone_marrow"
    saliva = "saliva"
    semen = "semen"
    other = "other"


class LabStatus(str, enum.Enum):
    pending = "pending"
    collected = "collected"
    received = "received"
    in_progress = "in_progress"
    completed = "completed"
    verified = "verified"
    cancelled = "cancelled"


class TestResultFlag(str, enum.Enum):
    normal = "normal"
    abnormal = "abnormal"
    critical_high = "critical_high"
    critical_low = "critical_low"
    panic = "panic"


class LabTest(Base, AuditMixin, TenantMixin):
    __tablename__ = "lab_tests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    test_name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    specimen_type: Mapped[SpecimenType] = mapped_column(Enum(SpecimenType), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    reference_range_low: Mapped[Optional[str]] = mapped_column(String(50))
    reference_range_high: Mapped[Optional[str]] = mapped_column(String(50))
    critical_low: Mapped[Optional[str]] = mapped_column(String(50))
    critical_high: Mapped[Optional[str]] = mapped_column(String(50))
    turnaround_hours: Mapped[Optional[int]] = mapped_column(Integer)
    requires_fasting: Mapped[bool] = mapped_column(Boolean, default=False)
    zambia_test: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    price_zmw: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        Index("idx_lab_test_code", "test_code"),
        Index("idx_lab_test_category", "category"),
    )


class LabPanel(Base, AuditMixin, TenantMixin):
    __tablename__ = "lab_panels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    panel_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    panel_name: Mapped[str] = mapped_column(String(300), nullable=False)
    tests: Mapped[Optional[dict]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    price_zmw: Mapped[Optional[float]] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class LabOrder(Base, AuditMixin, TenantMixin):
    __tablename__ = "lab_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    encounter_id: Mapped[Optional[str]] = mapped_column(String(255))
    ordering_provider: Mapped[Optional[str]] = mapped_column(String(200))
    ordering_provider_id: Mapped[Optional[str]] = mapped_column(String(255))
    clinical_notes: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="routine")
    status: Mapped[LabStatus] = mapped_column(Enum(LabStatus), default=LabStatus.pending)
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    collected_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    received_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    specimen_id: Mapped[Optional[str]] = mapped_column(String(100))
    specimen_type: Mapped[Optional[SpecimenType]] = mapped_column(Enum(SpecimenType))
    specimen_collected_by: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    results = relationship("LabResult", back_populates="order")

    __table_args__ = (
        Index("idx_lab_order_patient", "patient_id", "order_date"),
        Index("idx_lab_order_status", "status", "order_date"),
    )


class LabResult(Base, AuditMixin, TenantMixin):
    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_orders.id"), nullable=False, index=True
    )
    test_code: Mapped[str] = mapped_column(String(50), nullable=False)
    test_name: Mapped[str] = mapped_column(String(300), nullable=False)
    result_value: Mapped[Optional[str]] = mapped_column(Text)
    result_numeric: Mapped[Optional[float]] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    reference_range_low: Mapped[Optional[str]] = mapped_column(String(50))
    reference_range_high: Mapped[Optional[str]] = mapped_column(String(50))
    flag: Mapped[TestResultFlag] = mapped_column(Enum(TestResultFlag), default=TestResultFlag.normal)
    specimen_type: Mapped[Optional[str]] = mapped_column(String(100))
    result_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    performed_by: Mapped[Optional[str]] = mapped_column(String(200))
    verified_by: Mapped[Optional[str]] = mapped_column(String(200))
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_abnormal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)

    order = relationship("LabOrder", back_populates="results")

    __table_args__ = (
        Index("idx_lab_result_order", "order_id", "test_code"),
        Index("idx_lab_result_critical", "is_critical", "result_date"),
    )


class QualityControl(Base, AuditMixin, TenantMixin):
    __tablename__ = "quality_controls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_code: Mapped[str] = mapped_column(String(50), nullable=False)
    control_type: Mapped[str] = mapped_column(String(50), nullable=False)
    lot_number: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_value: Mapped[Optional[str]] = mapped_column(String(100))
    measured_value: Mapped[Optional[str]] = mapped_column(String(100))
    in_range: Mapped[bool] = mapped_column(Boolean, default=True)
    performed_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    performed_by: Mapped[Optional[str]] = mapped_column(String(200))
    equipment_used: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_qc_test_lot", "test_code", "lot_number"),
    )
