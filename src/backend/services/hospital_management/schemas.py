import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    BedStatus,
    ClaimStatus,
    HospitalLevel,
    PaymentMethod,
    PaymentStatus,
    ShiftType,
    StaffRole,
    TransactionType,
    WardType,
)


# ─── Hospital ──────────────────────────────────────────────────────────────────
class HospitalBase(BaseModel):
    name: str
    code: str
    level: HospitalLevel
    address_line: Optional[str] = None
    city: Optional[str] = None
    province: str
    district: str
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    bed_count: int = 0


class HospitalCreate(HospitalBase):
    pass


class HospitalResponse(HospitalBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Department ────────────────────────────────────────────────────────────────
class DepartmentCreate(BaseModel):
    name: str
    code: Optional[str] = None
    head_of_department: Optional[str] = None
    location: Optional[str] = None
    phone_extension: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: Optional[str] = None
    head_of_department: Optional[str] = None
    location: Optional[str] = None
    phone_extension: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class DepartmentUpdate(BaseModel):
    """Partial update for an existing department (admin only)."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=20)
    head_of_department: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    phone_extension: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


# ─── Ward ──────────────────────────────────────────────────────────────────────
class WardCreate(BaseModel):
    name: str
    code: str
    ward_type: WardType
    capacity: int
    gender_restriction: Optional[str] = None
    age_group: Optional[str] = None
    notes: Optional[str] = None


class WardResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    ward_type: WardType
    capacity: int
    current_occupancy: int
    gender_restriction: Optional[str] = None
    age_group: Optional[str] = None
    available_beds: int = 0
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ─── Bed ───────────────────────────────────────────────────────────────────────
class BedCreate(BaseModel):
    bed_label: str
    ward_id: uuid.UUID


class BedResponse(BaseModel):
    id: uuid.UUID
    bed_label: str
    ward_id: uuid.UUID
    status: BedStatus
    current_patient_id: Optional[uuid.UUID] = None
    current_encounter_id: Optional[uuid.UUID] = None
    occupied_since: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BedAssignment(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID


class AdmissionCreate(BaseModel):
    patient_id: uuid.UUID
    reason: str = Field(..., min_length=1, max_length=2000)
    notes: Optional[str] = Field(None, max_length=5000)


# ─── Staff ─────────────────────────────────────────────────────────────────────
class StaffCreate(BaseModel):
    user_id: Optional[str] = None
    first_name: str
    last_name: str
    role: StaffRole
    speciality: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    max_hours_per_week: int = 40


class StaffResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[str] = None
    first_name: str
    last_name: str
    role: StaffRole
    speciality: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    is_active: bool
    max_hours_per_week: int

    model_config = ConfigDict(from_attributes=True)


class StaffUpdate(BaseModel):
    """Partial update for an existing staff member / doctor (admin only)."""

    user_id: Optional[str] = Field(None, max_length=50)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[StaffRole] = None
    speciality: Optional[str] = Field(None, max_length=200)
    department_id: Optional[uuid.UUID] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    license_number: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    max_hours_per_week: Optional[int] = Field(None, ge=1, le=168)


# ─── Staff Schedule ────────────────────────────────────────────────────────────
class ScheduleCreate(BaseModel):
    staff_id: uuid.UUID
    shift_date: date
    shift_type: ShiftType
    start_time: time
    end_time: time
    ward_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

    @field_validator("end_time")
    @classmethod
    def validate_end_after_start(cls, v, info):
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    staff_id: uuid.UUID
    shift_date: date
    shift_type: ShiftType
    start_time: time
    end_time: time
    ward_id: Optional[uuid.UUID] = None
    is_confirmed: bool
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Inventory ─────────────────────────────────────────────────────────────────
class InventoryCreate(BaseModel):
    item_name: str
    item_code: str
    category: str
    description: Optional[str] = None
    quantity: Decimal = Decimal("0")
    unit: str
    unit_price_zmw: Decimal = Decimal("0")
    reorder_level: Decimal = Decimal("0")
    expiry_date: Optional[date] = None
    batch_number: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier: Optional[str] = None
    location: Optional[str] = None


class InventoryResponse(BaseModel):
    id: uuid.UUID
    item_name: str
    item_code: str
    category: str
    description: Optional[str] = None
    quantity: Decimal
    unit: str
    unit_price_zmw: Decimal
    reorder_level: Decimal
    expiry_date: Optional[date] = None
    batch_number: Optional[str] = None
    manufacturer: Optional[str] = None
    supplier: Optional[str] = None
    location: Optional[str] = None
    is_low_stock: bool = False

    model_config = ConfigDict(from_attributes=True)


# ─── Equipment ─────────────────────────────────────────────────────────────────
class EquipmentCreate(BaseModel):
    equipment_name: str
    equipment_code: str
    category: str
    model: Optional[str] = None
    serial_number: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    purchase_date: Optional[date] = None
    purchase_price_zmw: Optional[Decimal] = None
    warranty_expiry: Optional[date] = None
    notes: Optional[str] = None


class EquipmentResponse(BaseModel):
    id: uuid.UUID
    equipment_name: str
    equipment_code: str
    category: str
    model: Optional[str] = None
    serial_number: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    purchase_date: Optional[date] = None
    status: str
    last_maintenance_date: Optional[date] = None
    next_maintenance_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Financial Transaction ─────────────────────────────────────────────────────
class TransactionCreate(BaseModel):
    patient_id: Optional[uuid.UUID] = None
    encounter_id: Optional[uuid.UUID] = None
    transaction_type: TransactionType
    description: Optional[str] = None
    amount_zmw: Decimal
    discount_zmw: Decimal = Decimal("0")
    payment_method: Optional[PaymentMethod] = None
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    transaction_number: str
    patient_id: Optional[uuid.UUID] = None
    encounter_id: Optional[uuid.UUID] = None
    transaction_type: TransactionType
    description: Optional[str] = None
    amount_zmw: Decimal
    discount_zmw: Decimal
    total_zmw: Decimal
    paid_amount_zmw: Decimal
    balance_zmw: Decimal
    payment_status: PaymentStatus
    payment_method: Optional[PaymentMethod] = None
    transaction_date: datetime
    receipt_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Insurance Claim ───────────────────────────────────────────────────────────
class ClaimCreate(BaseModel):
    patient_id: uuid.UUID
    encounter_id: Optional[uuid.UUID] = None
    insurance_provider: str
    insurance_number: str
    is_nhima: bool = False
    diagnosis_codes: Optional[str] = None
    procedure_codes: Optional[str] = None
    medication_codes: Optional[str] = None
    total_amount_zmw: Decimal


class ClaimResponse(BaseModel):
    id: uuid.UUID
    claim_number: str
    patient_id: uuid.UUID
    encounter_id: Optional[uuid.UUID] = None
    insurance_provider: str
    insurance_number: str
    is_nhima: bool
    total_amount_zmw: Decimal
    approved_amount_zmw: Optional[Decimal] = None
    paid_amount_zmw: Optional[Decimal] = None
    status: ClaimStatus
    submission_date: Optional[datetime] = None
    approval_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
