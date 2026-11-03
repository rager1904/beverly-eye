from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, TenantMixin


class PrescriptionStatus(str, enum.Enum):
    active = "active"
    dispensed = "dispensed"
    partially_dispensed = "partially_dispensed"
    cancelled = "cancelled"
    expired = "expired"


class DispensationStatus(str, enum.Enum):
    pending = "pending"
    dispensed = "dispensed"
    verified = "verified"
    returned = "returned"


class InteractionSeverity(str, enum.Enum):
    minor = "minor"
    moderate = "moderate"
    major = "major"
    contraindicated = "contraindicated"


class FormularyItem(Base, AuditMixin, TenantMixin):
    __tablename__ = "formulary_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_name: Mapped[str] = mapped_column(String(300), nullable=False)
    generic_name: Mapped[Optional[str]] = mapped_column(String(300))
    dosage_form: Mapped[str] = mapped_column(String(50), nullable=False)
    strength: Mapped[Optional[str]] = mapped_column(String(100))
    therapeutic_class: Mapped[Optional[str]] = mapped_column(String(200))
    is_controlled: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_prescription: Mapped[bool] = mapped_column(Boolean, default=True)
    is_essential_medication: Mapped[bool] = mapped_column(Boolean, default=False)
    zambia_eml_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    max_daily_dosage: Mapped[Optional[str]] = mapped_column(String(100))
    common_side_effects: Mapped[Optional[str]] = mapped_column(Text)
    contraindications: Mapped[Optional[str]] = mapped_column(Text)
    unit_price_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_formulary_name", "medicine_name"),
        Index("idx_formulary_generic", "generic_name"),
        Index("idx_formulary_eml", "zambia_eml_listed"),
    )


class Prescription(Base, AuditMixin, TenantMixin):
    __tablename__ = "prescriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    encounter_id: Mapped[Optional[str]] = mapped_column(String(255))
    prescribing_provider: Mapped[str] = mapped_column(String(200), nullable=False)
    prescribing_provider_id: Mapped[Optional[str]] = mapped_column(String(255))
    diagnosis: Mapped[Optional[str]] = mapped_column(Text)
    prescription_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[PrescriptionStatus] = mapped_column(Enum(PrescriptionStatus), default=PrescriptionStatus.active)
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    total_cost_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    insurance_claim_id: Mapped[Optional[str]] = mapped_column(String(255))

    items = relationship("PrescriptionItem", back_populates="prescription")
    dispensations = relationship("Dispensation", back_populates="prescription")

    __table_args__ = (
        Index("idx_rx_patient", "patient_id", "prescription_date"),
        Index("idx_rx_provider", "prescribing_provider_id", "status"),
    )


class PrescriptionItem(Base, AuditMixin, TenantMixin):
    __tablename__ = "prescription_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False, index=True
    )
    medicine_name: Mapped[str] = mapped_column(String(300), nullable=False)
    generic_name: Mapped[Optional[str]] = mapped_column(String(300))
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(50), default="oral")
    duration_days: Mapped[Optional[int]] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_dispensed: Mapped[int] = mapped_column(Integer, default=0)
    refills: Mapped[int] = mapped_column(Integer, default=0)
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    substitution_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    prescription = relationship("Prescription", back_populates="items")


class Dispensation(Base, AuditMixin, TenantMixin):
    __tablename__ = "dispensations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False, index=True
    )
    prescription_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    medicine_name: Mapped[str] = mapped_column(String(300), nullable=False)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100))
    quantity_dispensed: Mapped[int] = mapped_column(Integer, nullable=False)
    dispensation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    dispensed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    verified_by: Mapped[Optional[str]] = mapped_column(String(200))
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[DispensationStatus] = mapped_column(Enum(DispensationStatus), default=DispensationStatus.pending)
    unit_price_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    total_price_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    prescription = relationship("Prescription", back_populates="dispensations")

    __table_args__ = (
        Index("idx_dispensation_date", "dispensation_date"),
    )


class DrugInteraction(Base, AuditMixin, TenantMixin):
    __tablename__ = "drug_interactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_a: Mapped[str] = mapped_column(String(300), nullable=False)
    drug_b: Mapped[str] = mapped_column(String(300), nullable=False)
    severity: Mapped[InteractionSeverity] = mapped_column(Enum(InteractionSeverity), nullable=False)
    mechanism: Mapped[Optional[str]] = mapped_column(Text)
    clinical_effect: Mapped[Optional[str]] = mapped_column(Text)
    recommendation: Mapped[Optional[str]] = mapped_column(Text)
    evidence_level: Mapped[Optional[str]] = mapped_column(String(50))
    source: Mapped[Optional[str]] = mapped_column(String(200))

    __table_args__ = (
        Index("idx_interaction_drugs", "drug_a", "drug_b", unique=True),
    )


class PharmacyInventory(Base, AuditMixin, TenantMixin):
    __tablename__ = "pharmacy_inventory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_name: Mapped[str] = mapped_column(String(300), nullable=False)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit_price_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)
    location: Mapped[Optional[str]] = mapped_column(String(200))
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("idx_pharm_inv_name", "medicine_name", "batch_number"),
        Index("idx_pharm_inv_expiry", "expiry_date"),
    )
