import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

from .models import (
    AllergySeverity,
    DiagnosisCertainty,
    DiagnosisType,
    EncounterStatus,
    EncounterType,
    Gender,
    ImmunizationStatus,
    MaritalStatus,
    MedicationStatus,
    NoteStatus,
    NoteType,
    OrderPriority,
    OrderStatus,
    OrderType,
    ProblemStatus,
    Province,
    ResultInterpretation,
)


# ─── Patient ────────────────────────────────────────────────────────────────────
class PatientBase(BaseModel):
    nrc_number: Optional[str] = Field(None, max_length=20, description="Zambia NRC number")
    smartcare_id: Optional[str] = Field(None, max_length=50)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: date
    gender: Gender
    marital_status: Optional[MaritalStatus] = None
    occupation: Optional[str] = Field(None, max_length=100)
    phone: str = Field(..., max_length=20)
    email: Optional[EmailStr] = None
    address_line: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    province: Optional[Province] = None
    district: Optional[str] = Field(None, max_length=100)
    nationality: Optional[str] = Field(None, max_length=100)
    emergency_contact_name: Optional[str] = Field(None, max_length=200)
    emergency_contact_phone: Optional[str] = Field(None, max_length=20)
    emergency_contact_relation: Optional[str] = Field(None, max_length=100)
    insurance_provider: Optional[str] = Field(None, max_length=200)
    insurance_number: Optional[str] = Field(None, max_length=50)
    insurance_expiry: Optional[date] = None
    nhima_member: bool = False
    nhima_number: Optional[str] = Field(None, max_length=50)
    language_preference: Optional[str] = "en"
    notes: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if v and not v.startswith("+"):
            v = "+260" + v.lstrip("0")
        if len(v) > 20:
            raise ValueError("Phone number must be at most 20 characters after normalization")
        return v


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    nrc_number: Optional[str] = None
    smartcare_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    marital_status: Optional[MaritalStatus] = None
    occupation: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    province: Optional[Province] = None
    district: Optional[str] = None
    nationality: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None
    insurance_expiry: Optional[date] = None
    nhima_member: Optional[bool] = None
    nhima_number: Optional[str] = None
    language_preference: Optional[str] = None
    notes: Optional[str] = None


class PatientResponse(PatientBase):
    id: uuid.UUID
    hospital_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PatientSummary(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Gender
    phone: str
    nrc_number: Optional[str] = None
    province: Optional[Province] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Encounter ──────────────────────────────────────────────────────────────────
class VitalsBase(BaseModel):
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[Decimal] = None
    oxygen_saturation: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    height: Optional[Decimal] = None
    bmi: Optional[Decimal] = None
    pain_score: Optional[int] = Field(None, ge=0, le=10)


class EncounterCreate(VitalsBase):
    patient_id: uuid.UUID
    encounter_type: EncounterType
    encounter_datetime: datetime
    chief_complaint: Optional[str] = None
    triage_notes: Optional[str] = None
    department: Optional[str] = None
    facility_id: Optional[str] = None
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None


class EncounterUpdate(BaseModel):
    encounter_type: Optional[EncounterType] = None
    status: Optional[EncounterStatus] = None
    chief_complaint: Optional[str] = None
    triage_notes: Optional[str] = None
    department: Optional[str] = None
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None


class EncounterResponse(VitalsBase):
    id: uuid.UUID
    patient_id: uuid.UUID
    hospital_id: uuid.UUID
    encounter_type: EncounterType
    encounter_datetime: datetime
    status: EncounterStatus
    chief_complaint: Optional[str] = None
    triage_notes: Optional[str] = None
    department: Optional[str] = None
    facility_id: Optional[str] = None
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Diagnosis ──────────────────────────────────────────────────────────────────
class DiagnosisCreate(BaseModel):
    encounter_id: uuid.UUID
    patient_id: uuid.UUID
    icd10_code: str
    icd10_description: str
    diagnosis_type: DiagnosisType
    certainty: DiagnosisCertainty = DiagnosisCertainty.confirmed
    sequence: Optional[int] = None
    is_chronic: bool = False
    onset_date: Optional[date] = None
    resolution_date: Optional[date] = None
    notes: Optional[str] = None


class DiagnosisUpdate(BaseModel):
    icd10_code: Optional[str] = None
    icd10_description: Optional[str] = None
    diagnosis_type: Optional[DiagnosisType] = None
    certainty: Optional[DiagnosisCertainty] = None
    sequence: Optional[int] = None
    is_chronic: Optional[bool] = None
    onset_date: Optional[date] = None
    resolution_date: Optional[date] = None
    notes: Optional[str] = None


class DiagnosisResponse(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    patient_id: uuid.UUID
    icd10_code: str
    icd10_description: str
    diagnosis_type: DiagnosisType
    certainty: DiagnosisCertainty
    sequence: Optional[int] = None
    is_chronic: bool
    onset_date: Optional[date] = None
    resolution_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Medication ─────────────────────────────────────────────────────────────────
class MedicationCreate(BaseModel):
    encounter_id: Optional[uuid.UUID] = None
    patient_id: uuid.UUID
    medication_name: str
    generic_name: Optional[str] = None
    dosage: Optional[str] = None
    dosage_unit: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    duration: Optional[int] = None
    duration_unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    refills: Optional[int] = 0
    prescribing_provider_id: Optional[str] = None
    prescribing_provider_name: Optional[str] = None
    price_zmw: Optional[Decimal] = None
    pharmacy_notes: Optional[str] = None
    is_antibiotic: bool = False
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class MedicationResponse(BaseModel):
    id: uuid.UUID
    encounter_id: Optional[uuid.UUID] = None
    patient_id: uuid.UUID
    medication_name: str
    generic_name: Optional[str] = None
    dosage: Optional[str] = None
    dosage_unit: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    duration: Optional[int] = None
    duration_unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    refills: Optional[int] = None
    prescribing_provider_id: Optional[str] = None
    prescribing_provider_name: Optional[str] = None
    adminitered_by: Optional[str] = None
    administered_at: Optional[datetime] = None
    status: MedicationStatus
    price_zmw: Optional[Decimal] = None
    is_antibiotic: bool
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Allergy ────────────────────────────────────────────────────────────────────
class AllergyCreate(BaseModel):
    patient_id: uuid.UUID
    allergen: str
    reaction: Optional[str] = None
    severity: AllergySeverity
    onset_date: Optional[date] = None
    is_drug_allergy: bool = False


class AllergyResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    allergen: str
    reaction: Optional[str] = None
    severity: AllergySeverity
    onset_date: Optional[date] = None
    status: str
    is_drug_allergy: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── ProblemList ────────────────────────────────────────────────────────────────
class ProblemCreate(BaseModel):
    patient_id: uuid.UUID
    problem_name: str
    icd10_code: Optional[str] = None
    icd10_description: Optional[str] = None
    onset_date: Optional[date] = None
    resolution_date: Optional[date] = None
    status: ProblemStatus = ProblemStatus.active
    is_chronic: bool = False
    notes: Optional[str] = None


class ProblemResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    problem_name: str
    icd10_code: Optional[str] = None
    icd10_description: Optional[str] = None
    onset_date: Optional[date] = None
    resolution_date: Optional[date] = None
    status: ProblemStatus
    is_chronic: bool
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Immunization ───────────────────────────────────────────────────────────────
class ImmunizationCreate(BaseModel):
    patient_id: uuid.UUID
    vaccine_type: str
    batch_number: Optional[str] = None
    administered_date: date
    administered_by: Optional[str] = None
    dose_number: Optional[int] = None
    total_doses: Optional[int] = None
    manufacturer: Optional[str] = None
    facility_id: Optional[str] = None
    notes: Optional[str] = None


class ImmunizationResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    vaccine_type: str
    batch_number: Optional[str] = None
    administered_date: date
    administered_by: Optional[str] = None
    dose_number: Optional[int] = None
    total_doses: Optional[int] = None
    manufacturer: Optional[str] = None
    facility_id: Optional[str] = None
    status: ImmunizationStatus
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── SocialHistory ──────────────────────────────────────────────────────────────
class SocialHistoryCreate(BaseModel):
    patient_id: uuid.UUID
    smoking_status: Optional[str] = None
    pack_years: Optional[Decimal] = None
    alcohol_consumption: Optional[str] = None
    substance_use: Optional[str] = None
    occupation: Optional[str] = None
    occupation_category: Optional[str] = None
    education_level: Optional[str] = None
    number_of_dependents: Optional[int] = None
    living_conditions: Optional[str] = None
    nutrition_status: Optional[str] = None
    physical_activity: Optional[str] = None
    notes: Optional[str] = None


class SocialHistoryResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    smoking_status: Optional[str] = None
    pack_years: Optional[Decimal] = None
    alcohol_consumption: Optional[str] = None
    substance_use: Optional[str] = None
    occupation: Optional[str] = None
    occupation_category: Optional[str] = None
    education_level: Optional[str] = None
    number_of_dependents: Optional[int] = None
    living_conditions: Optional[str] = None
    nutrition_status: Optional[str] = None
    physical_activity: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── FamilyHistory ──────────────────────────────────────────────────────────────
class FamilyHistoryCreate(BaseModel):
    patient_id: uuid.UUID
    relationship: str
    condition_name: str
    icd10_code: Optional[str] = None
    icd10_description: Optional[str] = None
    age_of_onset: Optional[int] = None
    deceased: Optional[bool] = None
    cause_of_death: Optional[str] = None
    notes: Optional[str] = None


class FamilyHistoryResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    relationship: str
    condition_name: str
    icd10_code: Optional[str] = None
    icd10_description: Optional[str] = None
    age_of_onset: Optional[int] = None
    deceased: Optional[bool] = None
    cause_of_death: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── ClinicalNote ───────────────────────────────────────────────────────────────
EyeNoteDetails = Annotated[dict[str, Annotated[str, Field(max_length=8000)]], Field(max_length=40)]


class ClinicalNoteCreate(BaseModel):
    eye_details: Optional[EyeNoteDetails] = None
    encounter_id: Optional[uuid.UUID] = None
    patient_id: uuid.UUID
    note_type: NoteType
    title: Optional[str] = Field(None, max_length=500)
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    procedure_code: Optional[str] = Field(None, max_length=20)
    procedure_description: Optional[str] = Field(None, max_length=500)
    authored_by: Optional[str] = None
    authored_datetime: Optional[datetime] = None
    status: NoteStatus = NoteStatus.draft
    is_confidential: bool = False


class ClinicalNoteUpdate(BaseModel):
    eye_details: Optional[EyeNoteDetails] = None
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=500)
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    procedure_code: Optional[str] = Field(None, max_length=20)
    procedure_description: Optional[str] = Field(None, max_length=500)
    status: Optional[NoteStatus] = None
    is_confidential: Optional[bool] = None


class ClinicalNoteResponse(BaseModel):
    eye_details: Optional[EyeNoteDetails] = None
    id: uuid.UUID
    encounter_id: Optional[uuid.UUID] = None
    patient_id: uuid.UUID
    note_type: NoteType
    title: Optional[str] = None
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    procedure_code: Optional[str] = None
    procedure_description: Optional[str] = None
    authored_by: str
    authored_datetime: datetime
    status: NoteStatus
    is_confidential: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Order ──────────────────────────────────────────────────────────────────────
class OrderCreate(BaseModel):
    encounter_id: Optional[uuid.UUID] = None
    patient_id: uuid.UUID
    order_type: OrderType
    order_code: str
    order_description: str
    priority: OrderPriority = OrderPriority.routine
    clinical_notes: Optional[str] = None
    instructions: Optional[str] = None
    diagnosis_id: Optional[uuid.UUID] = None
    specimen_type: Optional[str] = Field(None, min_length=1, max_length=100)


class OrderResponse(BaseModel):
    id: uuid.UUID
    encounter_id: Optional[uuid.UUID] = None
    patient_id: uuid.UUID
    order_type: OrderType
    order_code: str
    order_description: str
    priority: OrderPriority
    status: OrderStatus
    ordered_by: Optional[str] = None
    ordered_datetime: Optional[datetime] = None
    performed_by: Optional[str] = None
    performed_datetime: Optional[datetime] = None
    result_id: Optional[uuid.UUID] = None
    clinical_notes: Optional[str] = None
    instructions: Optional[str] = None
    specimen_type: Optional[str] = None
    specimen_id: Optional[str] = None
    collected_by: Optional[str] = None
    collected_datetime: Optional[datetime] = None
    received_by: Optional[str] = None
    received_datetime: Optional[datetime] = None
    verified_by: Optional[str] = None
    verified_datetime: Optional[datetime] = None
    created_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Result ─────────────────────────────────────────────────────────────────────
class ResultCreate(BaseModel):
    order_id: uuid.UUID
    patient_id: uuid.UUID
    result_type: str
    result_code: str
    result_description: str
    result_value: Optional[str] = None
    result_unit: Optional[str] = None
    reference_range_low: Optional[str] = None
    reference_range_high: Optional[str] = None
    interpretation: ResultInterpretation = ResultInterpretation.pending
    performed_by: Optional[str] = None
    performed_datetime: Optional[datetime] = None
    result_datetime: Optional[datetime] = None
    attachments: Optional[str] = None
    notes: Optional[str] = None


class SpecimenCollection(BaseModel):
    specimen_id: str = Field(..., min_length=1, max_length=100)
    specimen_type: Optional[str] = Field(None, min_length=1, max_length=100)
    collected_datetime: Optional[datetime] = None


class SpecimenReceipt(BaseModel):
    received_datetime: Optional[datetime] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class ResultResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    patient_id: uuid.UUID
    result_type: str
    result_code: str
    result_description: str
    result_value: Optional[str] = None
    result_unit: Optional[str] = None
    reference_range_low: Optional[str] = None
    reference_range_high: Optional[str] = None
    interpretation: ResultInterpretation
    performed_by: Optional[str] = None
    performed_datetime: Optional[datetime] = None
    result_datetime: Optional[datetime] = None
    notes: Optional[str] = None
    verified_by: Optional[str] = None
    verified_datetime: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Pagination ─────────────────────────────────────────────────────────────────
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int
    total_pages: int
