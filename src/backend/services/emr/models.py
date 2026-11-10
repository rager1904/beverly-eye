import enum
import uuid
from datetime import date, datetime
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
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, SoftDeleteMixin, TenantMixin


class EncounterType(str, enum.Enum):
    outpatient = "outpatient"
    inpatient = "inpatient"
    emergency = "emergency"
    telemedicine = "telemedicine"
    home_visit = "home_visit"
    consultation = "consultation"
    follow_up = "follow_up"


class EncounterStatus(str, enum.Enum):
    planned = "planned"
    in_progress = "in_progress"
    on_hold = "on_hold"
    completed = "completed"
    cancelled = "cancelled"
    discharged = "discharged"


class DiagnosisType(str, enum.Enum):
    admission = "admission"
    discharge = "discharge"
    primary = "primary"
    secondary = "secondary"
    working = "working"
    differential = "differential"


class DiagnosisCertainty(str, enum.Enum):
    confirmed = "confirmed"
    suspected = "suspected"
    ruled_out = "ruled_out"


class AllergySeverity(str, enum.Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"
    anaphylaxis = "anaphylaxis"


class MedicationStatus(str, enum.Enum):
    prescribed = "prescribed"
    administered = "administered"
    held = "held"
    discontinued = "discontinued"
    completed = "completed"


class ProblemStatus(str, enum.Enum):
    active = "active"
    resolved = "resolved"
    inactive = "inactive"


class NoteType(str, enum.Enum):
    soap = "SOAP"
    progress = "progress"
    procedure = "procedure"
    discharge_summary = "discharge_summary"
    consultation = "consultation"
    nursing = "nursing"
    referral = "referral"


class NoteStatus(str, enum.Enum):
    draft = "draft"
    final = "final"
    amended = "amended"
    cancelled = "cancelled"


class OrderType(str, enum.Enum):
    lab = "lab"
    imaging = "imaging"
    referral = "referral"
    procedure = "procedure"
    blood_bank = "blood_bank"


class OrderPriority(str, enum.Enum):
    routine = "routine"
    urgent = "urgent"
    stat = "stat"


class OrderStatus(str, enum.Enum):
    draft = "draft"
    ordered = "ordered"
    collected = "collected"
    received = "received"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    resulted = "resulted"
    verified = "verified"


class ResultInterpretation(str, enum.Enum):
    normal = "normal"
    abnormal = "abnormal"
    critical = "critical"
    pending = "pending"
    not_interpreted = "not_interpreted"


class ImmunizationStatus(str, enum.Enum):
    administered = "administered"
    missed = "missed"
    scheduled = "scheduled"
    contraindicated = "contraindicated"


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class MaritalStatus(str, enum.Enum):
    single = "single"
    married = "married"
    divorced = "divorced"
    widowed = "widowed"
    separated = "separated"


class Province(str, enum.Enum):
    central = "Central"
    copperbelt = "Copperbelt"
    eastern = "Eastern"
    luapula = "Luapula"
    lusaka = "Lusaka"
    muchinga = "Muchinga"
    northern = "Northern"
    north_western = "North_Western"
    southern = "Southern"
    western = "Western"


class Patient(Base, AuditMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nrc_number: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, index=True
    )
    smartcare_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[Optional[str]] = mapped_column(String(100))
    date_of_birth: Mapped[date] = mapped_column(Date)
    gender: Mapped[Gender] = mapped_column(Enum(Gender, native_enum=False))
    marital_status: Mapped[Optional[MaritalStatus]] = mapped_column(
        Enum(MaritalStatus, native_enum=False)
    )
    occupation: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(200))
    address_line: Mapped[Optional[str]] = mapped_column(String(500))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    province: Mapped[Optional[Province]] = mapped_column(Enum(Province, native_enum=False))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    nationality: Mapped[Optional[str]] = mapped_column(String(100))

    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(200))
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(20))
    emergency_contact_relation: Mapped[Optional[str]] = mapped_column(String(100))

    insurance_provider: Mapped[Optional[str]] = mapped_column(String(200))
    insurance_number: Mapped[Optional[str]] = mapped_column(String(50))
    insurance_expiry: Mapped[Optional[date]] = mapped_column(Date)
    nhima_member: Mapped[bool] = mapped_column(Boolean, default=False)
    nhima_number: Mapped[Optional[str]] = mapped_column(String(50))

    photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    language_preference: Mapped[Optional[str]] = mapped_column(String(50), default="en")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    encounters = orm_relationship("Encounter", back_populates="patient")
    diagnoses = orm_relationship("Diagnosis", back_populates="patient")
    medications = orm_relationship("Medication", back_populates="patient")
    allergies = orm_relationship("Allergy", back_populates="patient")
    problem_list = orm_relationship("ProblemList", back_populates="patient")
    immunizations = orm_relationship("Immunization", back_populates="patient")
    social_histories = orm_relationship("SocialHistory", back_populates="patient")
    family_histories = orm_relationship("FamilyHistory", back_populates="patient")
    clinical_notes = orm_relationship("ClinicalNote", back_populates="patient")
    orders = orm_relationship("Order", back_populates="patient")
    results = orm_relationship("Result", back_populates="patient")

    __table_args__ = (
        Index("idx_patients_name", "last_name", "first_name"),
        Index("idx_patients_hospital_nrc", "hospital_id", "nrc_number"),
    )


class Encounter(Base, AuditMixin, TenantMixin):
    __tablename__ = "encounters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    encounter_type: Mapped[EncounterType] = mapped_column(Enum(EncounterType))
    encounter_datetime: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[EncounterStatus] = mapped_column(
        Enum(EncounterStatus), default=EncounterStatus.planned
    )
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text)
    triage_notes: Mapped[Optional[str]] = mapped_column(Text)
    department: Mapped[Optional[str]] = mapped_column(String(100))
    facility_id: Mapped[Optional[str]] = mapped_column(String(50))

    blood_pressure_systolic: Mapped[Optional[int]] = mapped_column(Integer)
    blood_pressure_diastolic: Mapped[Optional[int]] = mapped_column(Integer)
    heart_rate: Mapped[Optional[int]] = mapped_column(Integer)
    respiratory_rate: Mapped[Optional[int]] = mapped_column(Integer)
    temperature: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    oxygen_saturation: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    height: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    bmi: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    pain_score: Mapped[Optional[int]] = mapped_column(Integer)
    provider_id: Mapped[Optional[str]] = mapped_column(String(50))
    provider_name: Mapped[Optional[str]] = mapped_column(String(200))

    patient = orm_relationship("Patient", back_populates="encounters")
    diagnoses = orm_relationship("Diagnosis", back_populates="encounter")
    medications = orm_relationship("Medication", back_populates="encounter")
    clinical_notes = orm_relationship("ClinicalNote", back_populates="encounter")
    orders = orm_relationship("Order", back_populates="encounter")

    __table_args__ = (
        Index("idx_encounters_patient", "patient_id", "encounter_datetime"),
        Index("idx_encounters_hospital_status", "hospital_id", "status"),
    )


class Diagnosis(Base, AuditMixin, TenantMixin):
    __tablename__ = "diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    icd10_code: Mapped[str] = mapped_column(String(10), index=True)
    icd10_description: Mapped[str] = mapped_column(String(500))
    diagnosis_type: Mapped[DiagnosisType] = mapped_column(Enum(DiagnosisType))
    certainty: Mapped[DiagnosisCertainty] = mapped_column(Enum(DiagnosisCertainty))
    sequence: Mapped[Optional[int]] = mapped_column(Integer)
    is_chronic: Mapped[bool] = mapped_column(Boolean, default=False)
    onset_date: Mapped[Optional[date]] = mapped_column(Date)
    resolution_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    encounter = orm_relationship("Encounter", back_populates="diagnoses")
    patient = orm_relationship("Patient", back_populates="diagnoses")

    __table_args__ = (Index("idx_diagnoses_icd10", "icd10_code", "hospital_id"),)


class Medication(Base, AuditMixin, TenantMixin):
    __tablename__ = "medications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    medication_name: Mapped[str] = mapped_column(String(300))
    generic_name: Mapped[Optional[str]] = mapped_column(String(300))
    dosage: Mapped[Optional[str]] = mapped_column(String(100))
    dosage_unit: Mapped[Optional[str]] = mapped_column(String(50))
    frequency: Mapped[Optional[str]] = mapped_column(String(100))
    route: Mapped[Optional[str]] = mapped_column(String(50))
    duration: Mapped[Optional[int]] = mapped_column(Integer)
    duration_unit: Mapped[Optional[str]] = mapped_column(String(20))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    refills: Mapped[Optional[int]] = mapped_column(Integer)
    prescribing_provider_id: Mapped[Optional[str]] = mapped_column(String(50))
    prescribing_provider_name: Mapped[Optional[str]] = mapped_column(String(200))
    administered_by: Mapped[Optional[str]] = mapped_column(String(200))
    administered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[MedicationStatus] = mapped_column(
        Enum(MedicationStatus), default=MedicationStatus.prescribed
    )
    price_zmw: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    pharmacy_notes: Mapped[Optional[str]] = mapped_column(Text)
    is_antibiotic: Mapped[bool] = mapped_column(Boolean, default=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

    encounter = orm_relationship("Encounter", back_populates="medications")
    patient = orm_relationship("Patient", back_populates="medications")


class Allergy(Base, AuditMixin, TenantMixin):
    __tablename__ = "allergies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    allergen: Mapped[str] = mapped_column(String(300))
    reaction: Mapped[Optional[str]] = mapped_column(String(500))
    severity: Mapped[AllergySeverity] = mapped_column(Enum(AllergySeverity))
    onset_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_drug_allergy: Mapped[bool] = mapped_column(Boolean, default=False)

    patient = orm_relationship("Patient", back_populates="allergies")


class ProblemList(Base, AuditMixin, TenantMixin):
    __tablename__ = "problem_list"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    problem_name: Mapped[str] = mapped_column(String(500))
    icd10_code: Mapped[Optional[str]] = mapped_column(String(10))
    icd10_description: Mapped[Optional[str]] = mapped_column(String(500))
    onset_date: Mapped[Optional[date]] = mapped_column(Date)
    resolution_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[ProblemStatus] = mapped_column(
        Enum(ProblemStatus), default=ProblemStatus.active
    )
    is_chronic: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    patient = orm_relationship("Patient", back_populates="problem_list")


class Immunization(Base, AuditMixin, TenantMixin):
    __tablename__ = "immunizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    vaccine_type: Mapped[str] = mapped_column(String(100))
    batch_number: Mapped[Optional[str]] = mapped_column(String(100))
    administered_date: Mapped[date] = mapped_column(Date)
    administered_by: Mapped[Optional[str]] = mapped_column(String(200))
    dose_number: Mapped[Optional[int]] = mapped_column(Integer)
    total_doses: Mapped[Optional[int]] = mapped_column(Integer)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(200))
    facility_id: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[ImmunizationStatus] = mapped_column(
        Enum(ImmunizationStatus), default=ImmunizationStatus.administered
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    patient = orm_relationship("Patient", back_populates="immunizations")


class SocialHistory(Base, AuditMixin, TenantMixin):
    __tablename__ = "social_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    smoking_status: Mapped[Optional[str]] = mapped_column(String(50))
    pack_years: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    alcohol_consumption: Mapped[Optional[str]] = mapped_column(String(100))
    substance_use: Mapped[Optional[str]] = mapped_column(String(200))
    occupation: Mapped[Optional[str]] = mapped_column(String(200))
    occupation_category: Mapped[Optional[str]] = mapped_column(String(100))
    education_level: Mapped[Optional[str]] = mapped_column(String(100))
    number_of_dependents: Mapped[Optional[int]] = mapped_column(Integer)
    living_conditions: Mapped[Optional[str]] = mapped_column(Text)
    nutrition_status: Mapped[Optional[str]] = mapped_column(String(100))
    physical_activity: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    patient = orm_relationship("Patient", back_populates="social_histories")


class FamilyHistory(Base, AuditMixin, TenantMixin):
    __tablename__ = "family_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    relationship: Mapped[str] = mapped_column(String(100))
    condition_name: Mapped[str] = mapped_column(String(300))
    icd10_code: Mapped[Optional[str]] = mapped_column(String(10))
    icd10_description: Mapped[Optional[str]] = mapped_column(String(500))
    age_of_onset: Mapped[Optional[int]] = mapped_column(Integer)
    deceased: Mapped[Optional[bool]] = mapped_column(Boolean)
    cause_of_death: Mapped[Optional[str]] = mapped_column(String(300))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    patient = orm_relationship("Patient", back_populates="family_histories")


class ClinicalNote(Base, AuditMixin, TenantMixin):
    __tablename__ = "clinical_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    note_type: Mapped[NoteType] = mapped_column(Enum(NoteType))
    title: Mapped[Optional[str]] = mapped_column(String(500))

    subjective: Mapped[Optional[str]] = mapped_column(Text)
    objective: Mapped[Optional[str]] = mapped_column(Text)
    assessment: Mapped[Optional[str]] = mapped_column(Text)
    plan: Mapped[Optional[str]] = mapped_column(Text)

    procedure_code: Mapped[Optional[str]] = mapped_column(String(20))
    procedure_description: Mapped[Optional[str]] = mapped_column(String(500))

    authored_by: Mapped[str] = mapped_column(String(200))
    authored_datetime: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[NoteStatus] = mapped_column(
        Enum(NoteStatus), default=NoteStatus.draft
    )
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)

    encounter = orm_relationship("Encounter", back_populates="clinical_notes")
    patient = orm_relationship("Patient", back_populates="clinical_notes")


class Order(Base, AuditMixin, TenantMixin):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType))
    order_code: Mapped[str] = mapped_column(String(50))
    order_description: Mapped[str] = mapped_column(String(500))
    priority: Mapped[OrderPriority] = mapped_column(
        Enum(OrderPriority), default=OrderPriority.routine
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.draft
    )
    ordered_by: Mapped[Optional[str]] = mapped_column(String(200))
    ordered_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    performed_by: Mapped[Optional[str]] = mapped_column(String(200))
    performed_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    result_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    clinical_notes: Mapped[Optional[str]] = mapped_column(Text)
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    diagnosis_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    specimen_type: Mapped[Optional[str]] = mapped_column(String(100))
    specimen_id: Mapped[Optional[str]] = mapped_column(String(100))
    collected_by: Mapped[Optional[str]] = mapped_column(String(200))
    collected_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    received_by: Mapped[Optional[str]] = mapped_column(String(200))
    received_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    verified_by: Mapped[Optional[str]] = mapped_column(String(200))
    verified_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)

    encounter = orm_relationship("Encounter", back_populates="orders")
    patient = orm_relationship("Patient", back_populates="orders")
    results = orm_relationship("Result", back_populates="order")

    __table_args__ = (
        Index("idx_orders_status", "status", "hospital_id"),
        UniqueConstraint("hospital_id", "specimen_id", name="uq_orders_hospital_specimen"),
    )


class Result(Base, AuditMixin, TenantMixin):
    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    result_type: Mapped[str] = mapped_column(String(50))
    result_code: Mapped[str] = mapped_column(String(50))
    result_description: Mapped[str] = mapped_column(String(500))
    result_value: Mapped[Optional[str]] = mapped_column(Text)
    result_unit: Mapped[Optional[str]] = mapped_column(String(50))
    reference_range_low: Mapped[Optional[str]] = mapped_column(String(50))
    reference_range_high: Mapped[Optional[str]] = mapped_column(String(50))
    interpretation: Mapped[ResultInterpretation] = mapped_column(
        Enum(ResultInterpretation), default=ResultInterpretation.pending
    )
    performed_by: Mapped[Optional[str]] = mapped_column(String(200))
    performed_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    result_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    attachments: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    verified_by: Mapped[Optional[str]] = mapped_column(String(200))
    verified_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime)

    order = orm_relationship("Order", back_populates="results")
    patient = orm_relationship("Patient", back_populates="results")
