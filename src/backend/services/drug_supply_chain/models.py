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
from src.backend.mixins import AuditMixin, SoftDeleteMixin, TenantMixin


class DosageForm(str, enum.Enum):
    tablet = "tablet"
    capsule = "capsule"
    injection = "injection"
    syrup = "syrup"
    suspension = "suspension"
    cream = "cream"
    ointment = "ointment"
    drops = "drops"
    inhaler = "inhaler"
    suppository = "suppository"
    powder = "powder"
    granule = "granule"
    solution = "solution"
    patch = "patch"
    implant = "implant"


class DrugCategory(str, enum.Enum):
    antibiotic = "antibiotic"
    antimalarial = "antimalarial"
    antiretroviral = "antiretroviral"
    antihypertensive = "antihypertensive"
    antidiabetic = "antidiabetic"
    vaccine = "vaccine"
    analgesic = "analgesic"
    antiinflammatory = "antiinflammatory"
    antifungal = "antifungal"
    antiparasitic = "antiparasitic"
    tb_medication = "tb_medication"
    nutritional_supplement = "nutritional_supplement"
    iv_fluid = "iv_fluid"
    anesthetic = "anesthetic"
    psychiatric = "psychiatric"
    maternal_health = "maternal_health"
    other = "other"


class OrderStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    shipped = "shipped"
    received = "received"
    cancelled = "cancelled"


class MovementType(str, enum.Enum):
    receipt = "receipt"
    dispensation = "dispensation"
    transfer_in = "transfer_in"
    transfer_out = "transfer_out"
    adjustment = "adjustment"
    expiry_disposal = "expiry_disposal"
    return_to_supplier = "return_to_supplier"


class Medicine(Base, AuditMixin, TenantMixin):
    __tablename__ = "medicines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    generic_name: Mapped[Optional[str]] = mapped_column(String(300))
    category: Mapped[DrugCategory] = mapped_column(Enum(DrugCategory), nullable=False)
    dosage_form: Mapped[DosageForm] = mapped_column(Enum(DosageForm), nullable=False)
    strength: Mapped[Optional[str]] = mapped_column(String(100))
    manufacturer: Mapped[Optional[str]] = mapped_column(String(300))
    supplier_id: Mapped[Optional[str]] = mapped_column(String(255))
    is_essential_medicine: Mapped[bool] = mapped_column(Boolean, default=False)
    is_controlled_substance: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_prescription: Mapped[bool] = mapped_column(Boolean, default=True)
    unit_of_measure: Mapped[str] = mapped_column(String(50), default="tablet")
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit_price_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    storage_conditions: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    who_eml_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    zambia_eml_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    zambia_eml_level: Mapped[Optional[str]] = mapped_column(String(50))

    stock_levels = relationship("StockLevel", back_populates="medicine")
    movements = relationship("StockMovement", back_populates="medicine")

    __table_args__ = (
        Index("idx_medicine_name", "name"),
        Index("idx_medicine_category", "category"),
        Index("idx_medicine_essential", "is_essential_medicine"),
        Index("idx_medicine_generic", "generic_name"),
    )


class Supplier(Base, AuditMixin, TenantMixin):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    contact_person: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    address: Mapped[Optional[str]] = mapped_column(String(500))
    license_number: Mapped[Optional[str]] = mapped_column(String(100))
    contract_start_date: Mapped[Optional[date]] = mapped_column(Date)
    contract_end_date: Mapped[Optional[date]] = mapped_column(Date)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(200))
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class PurchaseOrder(Base, AuditMixin, TenantMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.draft)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(Date)
    received_date: Mapped[Optional[date]] = mapped_column(Date)
    items: Mapped[Optional[dict]] = mapped_column(Text)
    total_amount_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    approved_by: Mapped[Optional[str]] = mapped_column(String(200))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    supplier = relationship("Supplier", back_populates="purchase_orders")

    __table_args__ = (
        Index("idx_po_order_number", "order_number"),
        Index("idx_po_status", "status", "order_date"),
    )


class StockLevel(Base, AuditMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "stock_levels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100))
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(200))
    unit_cost_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    is_quarantined: Mapped[bool] = mapped_column(Boolean, default=False)

    medicine = relationship("Medicine", back_populates="stock_levels")

    __table_args__ = (
        Index("idx_stock_medicine_batch", "medicine_id", "batch_number"),
        Index("idx_stock_expiry", "expiry_date"),
    )


class StockMovement(Base, AuditMixin, TenantMixin):
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False, index=True
    )
    movement_type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100))
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)
    reference_type: Mapped[Optional[str]] = mapped_column(String(100))
    reference_id: Mapped[Optional[str]] = mapped_column(String(255))
    unit_cost_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    total_cost_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    movement_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    performed_by: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    medicine = relationship("Medicine", back_populates="movements")

    __table_args__ = (
        Index("idx_stock_movement_type", "movement_type", "movement_date"),
        Index("idx_stock_movement_medicine", "medicine_id", "movement_date"),
    )


class ExpiryTracking(Base, AuditMixin, TenantMixin):
    __tablename__ = "expiry_tracking"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False, index=True
    )
    medicine_name: Mapped[str] = mapped_column(String(300), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_at_risk: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    total_value_at_risk_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    days_until_expiry: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="active")
    disposed: Mapped[bool] = mapped_column(Boolean, default=False)
    disposal_date: Mapped[Optional[date]] = mapped_column(Date)
    disposed_by: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_expiry_batch", "batch_number", "expiry_date"),
        Index("idx_expiry_date", "expiry_date"),
    )


class StockoutPrediction(Base, AuditMixin, TenantMixin):
    __tablename__ = "stockout_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False, index=True
    )
    medicine_name: Mapped[str] = mapped_column(String(300), nullable=False)
    current_stock: Mapped[int] = mapped_column(Integer, default=0)
    daily_consumption_rate: Mapped[float] = mapped_column(Float, default=0.0)
    days_until_stockout: Mapped[int] = mapped_column(Integer, default=0)
    predicted_stockout_date: Mapped[Optional[date]] = mapped_column(Date)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    recommended_order_quantity: Mapped[int] = mapped_column(Integer, default=0)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="v1")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_prediction_medicine", "medicine_id", "prediction_date"),
        Index("idx_prediction_risk", "risk_level", "predicted_stockout_date"),
    )
