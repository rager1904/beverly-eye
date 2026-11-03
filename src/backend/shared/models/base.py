from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

DataT = TypeVar("DataT")


# ---- Enums ----
class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    NURSE = "nurse"
    CLINICAL_OFFICER = "clinical_officer"
    MIDWIFE = "midwife"
    COMMUNITY_HEALTH_WORKER = "community_health_worker"
    PHARMACIST = "pharmacist"
    LAB_TECHNICIAN = "lab_technician"
    RADIOLOGIST = "radiologist"
    MEDICAL_RECORDS = "medical_records"
    ADMINISTRATOR = "administrator"
    HOSPITAL_ADMIN = "hospital_admin"
    DISTRICT_HEALTH_OFFICER = "district_health_officer"
    PROVINCIAL_HEALTH_DIRECTOR = "provincial_health_director"
    MOH_OFFICIAL = "moh_official"
    SYSTEM_ADMIN = "system_admin"
    SUPER_ADMIN = "super_admin"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class EncounterType(str, Enum):
    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    EMERGENCY = "emergency"
    TELEMEDICINE = "telemedicine"
    COMMUNITY_VISIT = "community_visit"
    HOME_VISIT = "home_visit"
    FOLLOW_UP = "follow_up"
    MATERNAL_HEALTH = "maternal_health"
    IMMUNIZATION = "immunization"
    LAB_RESULT = "lab_result"
    REFERRAL = "referral"


class Province(str, Enum):
    CENTRAL = "Central"
    COPPERBELT = "Copperbelt"
    EASTERN = "Eastern"
    LUAPULA = "Luapula"
    LUSAKA = "Lusaka"
    MUCHINGA = "Muchinga"
    NORTHERN = "Northern"
    NORTH_WESTERN = "North-Western"
    SOUTHERN = "Southern"
    WESTERN = "Western"


class Currency(str, Enum):
    ZMW = "ZMW"
    USD = "USD"
    ZAR = "ZAR"
    KES = "KES"
    NGN = "NGN"
    TZS = "TZS"
    UGX = "UGX"
    RWF = "RWF"
    GHS = "GHS"


class Language(str, Enum):
    ENGLISH = "en"
    SWAHILI = "sw"
    CHEWA = "ny"
    BEMBA = "bem"
    SHONA = "sn"
    ZULU = "zu"
    XHOSA = "xh"
    AFRIKAANS = "af"


class DiseaseStatus(str, Enum):
    SUSPECTED = "suspected"
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    NEGATIVE = "negative"
    RECOVERED = "recovered"
    DECEASED = "deceased"
    UNDER_TREATMENT = "under_treatment"
    LOST_TO_FOLLOW_UP = "lost_to_follow_up"


# ---- API Response models ----
class APIResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str = "OK"
    data: Optional[DataT] = None
    error: Optional[str] = None
    request_id: Optional[str] = None

    model_config = {"extra": "ignore"}


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str = "An error occurred"
    error_code: Optional[str] = None
    errors: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None

    model_config = {"extra": "ignore"}


class PaginationMeta(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=1000)
    total_items: int = Field(default=0, ge=0)
    total_pages: int = Field(default=0, ge=0)
    has_next: bool = False
    has_previous: bool = False

    model_config = {"extra": "ignore"}


class PaginatedResponse(APIResponse, Generic[DataT]):
    pagination: Optional[PaginationMeta] = None


# ---- Health / Status ----
class HealthStatus(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service: str
    version: str
    environment: str
    uptime_seconds: float
    checks: dict[str, Any]


# ---- Tenant models ----
class TenantInfo(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    hospital_type: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    is_active: bool = True


class HospitalConfig(BaseModel):
    hospital_id: uuid.UUID
    name: str
    code: str
    province: Province = Province.LUSAKA
    district: str = "Lusaka"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    level: str = Field(default="district", pattern="^(clinic|health_post|district|provincial|tertiary|national)$")
    beds_count: int = Field(default=0, ge=0)
    is_public: bool = True
    is_active: bool = True
    timezone: str = "Africa/Lusaka"


# ---- User models ----
class UserBase(BaseModel):
    id: uuid.UUID
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: str
    last_name: str
    role: UserRole
    hospital_id: Optional[uuid.UUID] = None
    is_active: bool = True
    nupi: Optional[str] = None
    national_id: Optional[str] = None
    province: Optional[Province] = None
    district: Optional[str] = None
    facility_id: Optional[str] = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: UserRole
    hospital_id: Optional[uuid.UUID] = None
    password: str = Field(min_length=8, max_length=128)
    national_id: Optional[str] = None
    province: Optional[Province] = None
    district: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    created_at: datetime
    updated_at: datetime


# ---- Audit models ----
class AuditEntry(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    action: str
    resource: str
    resource_id: Optional[str] = None
    actor_id: Optional[str] = None
    hospital_id: Optional[str] = None
    outcome: str
    details: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    model_config = {"from_attributes": True}


# ---- Money ----
class Money(BaseModel):
    amount: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    currency: Currency = Currency.ZMW


# ---- Pagination helper ----
class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=1000)
    sort_by: Optional[str] = None
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")


def paginate(page: int, page_size: int, total_items: int) -> PaginationMeta:
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )
