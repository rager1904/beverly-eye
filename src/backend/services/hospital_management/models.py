import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, SoftDeleteMixin, TenantMixin


class HospitalLevel(str, enum.Enum):
    level_1 = "Level_1"
    level_2 = "Level_2"
    level_3 = "Level_3"
    level_4 = "Level_4"
    health_post = "Health_Post"
    health_center = "Health_Center"
    district_hospital = "District_Hospital"
    provincial_hospital = "Provincial_Hospital"
    tertiary_hospital = "Tertiary_Hospital"
    specialized_hospital = "Specialized_Hospital"


class WardType(str, enum.Enum):
    general = "general"
    maternity = "maternity"
    pediatric = "pediatric"
    surgical = "surgical"
    icu = "icu"
    nicu = "nicu"
    psychiatric = "psychiatric"
    isolation = "isolation"
    emergency = "emergency"
    outpatient = "outpatient"


class BedStatus(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    reserved = "reserved"
    maintenance = "maintenance"
    cleaning = "cleaning"


class StaffRole(str, enum.Enum):
    doctor = "doctor"
    nurse = "nurse"
    midwife = "midwife"
    clinical_officer = "clinical_officer"
    pharmacist = "pharmacist"
    lab_technician = "lab_technician"
    radiographer = "radiographer"
    administrator = "administrator"
    accountant = "accountant"
    records_officer = "records_officer"
    community_health_worker = "community_health_worker"
    cleaner = "cleaner"
    security = "security"


class ShiftType(str, enum.Enum):
    morning = "morning"
    afternoon = "afternoon"
    night = "night"
    on_call = "on_call"
    off = "off"


class TransactionType(str, enum.Enum):
    consultation = "consultation"
    admission = "admission"
    medication = "medication"
    lab = "lab"
    imaging = "imaging"
    procedure = "procedure"
    surgery = "surgery"
    maternity = "maternity"
    pharmacy = "pharmacy"
    other = "other"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    partial = "partial"
    paid = "paid"
    waived = "waived"
    refunded = "refunded"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    mobile_money = "mobile_money"
    insurance = "insurance"
    nhima = "nhima"
    bank_transfer = "bank_transfer"
    card = "card"


class ClaimStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    processing = "processing"
    approved = "approved"
    rejected = "rejected"
    paid = "paid"
    appealed = "appealed"


class Hospital(Base, AuditMixin):
    __tablename__ = "hospitals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(300))
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    level: Mapped[HospitalLevel] = mapped_column(Enum(HospitalLevel))
    address_line: Mapped[Optional[str]] = mapped_column(String(500))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    province: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    website: Mapped[Optional[str]] = mapped_column(String(200))
    bed_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    departments = relationship("Department", back_populates="hospital")
    wards = relationship("Ward", back_populates="hospital")
    staff_members = relationship("Staff", back_populates="hospital")


class Department(Base, AuditMixin, TenantMixin):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[Optional[str]] = mapped_column(String(20))
    head_of_department: Mapped[Optional[str]] = mapped_column(String(200))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    phone_extension: Mapped[Optional[str]] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    hospital_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hospitals.id")
    )
    hospital = relationship("Hospital", back_populates="departments")


class Ward(Base, AuditMixin, TenantMixin):
    __tablename__ = "wards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(20))
    ward_type: Mapped[WardType] = mapped_column(Enum(WardType))
    capacity: Mapped[int] = mapped_column(Integer)
    current_occupancy: Mapped[int] = mapped_column(Integer, default=0)
    gender_restriction: Mapped[Optional[str]] = mapped_column(String(20))
    age_group: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    hospital_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hospitals.id")
    )
    hospital = relationship("Hospital", back_populates="wards")
    beds = relationship("Bed", back_populates="ward")

    __table_args__ = (Index("idx_ward_hospital_type", "hospital_id", "ward_type"),)


class Bed(Base, AuditMixin, TenantMixin):
    __tablename__ = "beds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bed_label: Mapped[str] = mapped_column(String(50))
    ward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wards.id"), index=True
    )
    status: Mapped[BedStatus] = mapped_column(
        Enum(BedStatus), default=BedStatus.available
    )
    current_patient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True)
    )
    current_encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True)
    )
    occupied_since: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    ward = relationship("Ward", back_populates="beds")

    __table_args__ = (
        Index("idx_bed_ward_status", "ward_id", "status"),
        UniqueConstraint("ward_id", "bed_label", name="uq_bed_label_per_ward"),
    )


class Staff(Base, AuditMixin, TenantMixin):
    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[StaffRole] = mapped_column(Enum(StaffRole))
    speciality: Mapped[Optional[str]] = mapped_column(String(200))
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id")
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    license_number: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_hours_per_week: Mapped[int] = mapped_column(Integer, default=40)

    hospital_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hospitals.id")
    )
    hospital = relationship("Hospital", back_populates="staff_members")
    schedules = relationship("StaffSchedule", back_populates="staff")


class StaffSchedule(Base, AuditMixin, TenantMixin):
    __tablename__ = "staff_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff.id"), index=True
    )
    shift_date: Mapped[date] = mapped_column(Date)
    shift_type: Mapped[ShiftType] = mapped_column(Enum(ShiftType))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    ward_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wards.id")
    )
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    staff = relationship("Staff", back_populates="schedules")

    __table_args__ = (
        Index("idx_schedule_staff_date", "staff_id", "shift_date"),
        UniqueConstraint("staff_id", "shift_date", "shift_type", name="uq_staff_shift"),
    )


class Inventory(Base, AuditMixin, TenantMixin):
    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_name: Mapped[str] = mapped_column(String(300))
    item_code: Mapped[str] = mapped_column(String(50), index=True)
    category: Mapped[str] = mapped_column(
        String(50)
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    unit: Mapped[str] = mapped_column(String(50))
    unit_price_zmw: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100))
    manufacturer: Mapped[Optional[str]] = mapped_column(String(200))
    supplier: Mapped[Optional[str]] = mapped_column(String(200))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("idx_inventory_category", "category", "hospital_id"),
        Index("idx_inventory_low_stock", "quantity", "reorder_level"),
    )


class Equipment(Base, AuditMixin, TenantMixin):
    __tablename__ = "equipment"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    equipment_name: Mapped[str] = mapped_column(String(300))
    equipment_code: Mapped[str] = mapped_column(String(50), unique=True)
    category: Mapped[str] = mapped_column(String(50))
    model: Mapped[Optional[str]] = mapped_column(String(200))
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id")
    )
    purchase_date: Mapped[Optional[date]] = mapped_column(Date)
    purchase_price_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    warranty_expiry: Mapped[Optional[date]] = mapped_column(Date)
    last_maintenance_date: Mapped[Optional[date]] = mapped_column(Date)
    next_maintenance_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="operational")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class FinancialTransaction(Base, AuditMixin, TenantMixin):
    __tablename__ = "financial_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transaction_number: Mapped[str] = mapped_column(String(50), unique=True)
    patient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), index=True
    )
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    description: Mapped[Optional[str]] = mapped_column(String(500))
    amount_zmw: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount_zmw: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_zmw: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_amount_zmw: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    balance_zmw: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.pending
    )
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(Enum(PaymentMethod))
    transaction_date: Mapped[datetime] = mapped_column(DateTime)
    receipt_number: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_transaction_patient", "patient_id", "transaction_date"),
        Index("idx_transaction_status", "payment_status", "hospital_id"),
    )


class InsuranceClaim(Base, AuditMixin, TenantMixin):
    __tablename__ = "insurance_claims"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    claim_number: Mapped[str] = mapped_column(String(50), unique=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True
    )
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    insurance_provider: Mapped[str] = mapped_column(String(200))
    insurance_number: Mapped[str] = mapped_column(String(50))
    is_nhima: Mapped[bool] = mapped_column(Boolean, default=False)

    diagnosis_codes: Mapped[Optional[str]] = mapped_column(Text)
    procedure_codes: Mapped[Optional[str]] = mapped_column(Text)
    medication_codes: Mapped[Optional[str]] = mapped_column(Text)

    total_amount_zmw: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    approved_amount_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    paid_amount_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus), default=ClaimStatus.draft
    )
    submission_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    approval_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    appeal_notes: Mapped[Optional[str]] = mapped_column(Text)
    documents: Mapped[Optional[str]] = mapped_column(Text)
