from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, SoftDeleteMixin, TenantMixin


class NotifiableDisease(str, enum.Enum):
    malaria = "Malaria"
    hiv = "HIV/AIDS"
    tb = "Tuberculosis"
    cholera = "Cholera"
    covid19 = "COVID-19"
    measles = "Measles"
    polio = "Polio"
    ebola = "Ebola"
    yellow_fever = "Yellow Fever"
    meningitis = "Meningitis"
    typhoid = "Typhoid"
    dysentery = "Dysentery"
    rabies = "Rabies"
    maternal_death = "Maternal Death"
    neonatal_tetanus = "Neonatal Tetanus"
    guinea_worm = "Guinea Worm"
    leprosy = "Leprosy"
    trypanosomiasis = "Trypanosomiasis"
    schistosomiasis = "Schistosomiasis"
    lymphatic_filariasis = "Lymphatic Filariasis"
    onchocerciasis = "Onchocerciasis"
    anthrax = "Anthrax"
    plague = "Plague"
    viral_hemorrhagic_fever = "Viral Hemorrhagic Fever"


class CaseStatus(str, enum.Enum):
    suspected = "suspected"
    probable = "probable"
    confirmed = "confirmed"
    discarded = "discarded"


class CaseSeverity(str, enum.Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"
    critical = "critical"
    fatal = "fatal"


class OutbreakStatus(str, enum.Enum):
    potential = "potential"
    active = "active"
    contained = "contained"
    resolved = "resolved"


class ReportType(str, enum.Enum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    annual = "annual"
    outbreak = "outbreak"
    special = "special"


class DiseaseCase(Base, AuditMixin, TenantMixin):
    __tablename__ = "disease_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    disease: Mapped[NotifiableDisease] = mapped_column(Enum(NotifiableDisease), nullable=False, index=True)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.suspected)
    severity: Mapped[CaseSeverity] = mapped_column(Enum(CaseSeverity), default=CaseSeverity.mild)
    patient_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    patient_name: Mapped[Optional[str]] = mapped_column(String(200))
    patient_age: Mapped[Optional[int]] = mapped_column(Integer)
    patient_gender: Mapped[Optional[str]] = mapped_column(String(20))
    nrc_number: Mapped[Optional[str]] = mapped_column(String(20))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(String(500))
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    facility_name: Mapped[Optional[str]] = mapped_column(String(200))
    location_lat: Mapped[Optional[Decimal]] = mapped_column(Float)
    location_lng: Mapped[Optional[Decimal]] = mapped_column(Float)
    onset_date: Mapped[Optional[date]] = mapped_column(Date)
    diagnosis_date: Mapped[date] = mapped_column(Date, nullable=False)
    confirmation_method: Mapped[Optional[str]] = mapped_column(String(100))
    symptoms: Mapped[Optional[dict]] = mapped_column(Text)
    risk_factors: Mapped[Optional[str]] = mapped_column(Text)
    occupation: Mapped[Optional[str]] = mapped_column(String(200))
    travel_history: Mapped[Optional[str]] = mapped_column(Text)
    exposure_history: Mapped[Optional[str]] = mapped_column(Text)
    outcome: Mapped[Optional[str]] = mapped_column(String(50))
    outcome_date: Mapped[Optional[date]] = mapped_column(Date)
    hospitalization_required: Mapped[bool] = mapped_column(Boolean, default=False)
    hospitalization_dates: Mapped[Optional[str]] = mapped_column(String(200))
    reported_by: Mapped[Optional[str]] = mapped_column(String(200))
    reporter_contact: Mapped[Optional[str]] = mapped_column(String(20))
    dhis2_event_id: Mapped[Optional[str]] = mapped_column(String(100))
    who_reported: Mapped[bool] = mapped_column(Boolean, default=False)
    who_report_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    lab_confirmations = orm_relationship("LabConfirmation", back_populates="disease_case")
    contacts = orm_relationship("ContactTracing", back_populates="disease_case")

    __table_args__ = (
        Index("idx_disease_cases_disease_status", "disease", "status"),
        Index("idx_disease_cases_diagnosis_date", "diagnosis_date"),
        Index("idx_disease_cases_district_disease", "district", "disease"),
    )


class OutbreakAlert(Base, AuditMixin, TenantMixin):
    __tablename__ = "outbreak_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    disease: Mapped[NotifiableDisease] = mapped_column(Enum(NotifiableDisease), nullable=False, index=True)
    status: Mapped[OutbreakStatus] = mapped_column(Enum(OutbreakStatus), default=OutbreakStatus.potential)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    facility_name: Mapped[Optional[str]] = mapped_column(String(200))
    detected_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, default=1)
    suspected_cases: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_cases: Mapped[int] = mapped_column(Integer, default=0)
    deaths: Mapped[int] = mapped_column(Integer, default=0)
    attack_rate: Mapped[Optional[float]] = mapped_column(Float)
    case_fatality_rate: Mapped[Optional[float]] = mapped_column(Float)
    location_lat: Mapped[Optional[float]] = mapped_column(Float)
    location_lng: Mapped[Optional[float]] = mapped_column(Float)
    affected_population: Mapped[Optional[int]] = mapped_column(Integer)
    response_team_activated: Mapped[bool] = mapped_column(Boolean, default=False)
    response_actions: Mapped[Optional[str]] = mapped_column(Text)
    escalated_to_moh: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    contained_date: Mapped[Optional[date]] = mapped_column(Date)
    resolved_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_outbreak_disease_status", "disease", "status"),
        Index("idx_outbreak_district", "district"),
        Index("idx_outbreak_detected_date", "detected_date"),
    )


class SurveillanceReport(Base, AuditMixin, TenantMixin):
    __tablename__ = "surveillance_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    district: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    province: Mapped[Optional[str]] = mapped_column(String(100))
    facility_name: Mapped[Optional[str]] = mapped_column(String(200))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    data: Mapped[Optional[dict]] = mapped_column(Text)
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    total_deaths: Mapped[int] = mapped_column(Integer, default=0)
    diseases_reported: Mapped[Optional[dict]] = mapped_column(Text)
    submitted_to_moh: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    submitted_by: Mapped[Optional[str]] = mapped_column(String(200))
    dhis2_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    dhis2_submission_id: Mapped[Optional[str]] = mapped_column(String(100))
    who_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    report_file_url: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="draft")

    __table_args__ = (
        Index("idx_surveillance_report_period", "period_start", "period_end"),
    )


class LabConfirmation(Base, AuditMixin, TenantMixin):
    __tablename__ = "lab_confirmations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    disease_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disease_cases.id"), nullable=False
    )
    test_type: Mapped[str] = mapped_column(String(200), nullable=False)
    test_result: Mapped[str] = mapped_column(String(50), nullable=False)
    test_date: Mapped[date] = mapped_column(Date, nullable=False)
    lab_name: Mapped[Optional[str]] = mapped_column(String(200))
    lab_technician: Mapped[Optional[str]] = mapped_column(String(200))
    specimen_type: Mapped[Optional[str]] = mapped_column(String(100))
    specimen_collection_date: Mapped[Optional[date]] = mapped_column(Date)
    result_verified_by: Mapped[Optional[str]] = mapped_column(String(200))
    result_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    result_details: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    disease_case = orm_relationship("DiseaseCase", back_populates="lab_confirmations")


class ContactTracing(Base, AuditMixin, TenantMixin):
    __tablename__ = "contact_tracing"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    disease_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disease_cases.id"), nullable=False
    )
    contact_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20))
    contact_address: Mapped[Optional[str]] = mapped_column(String(500))
    relationship: Mapped[Optional[str]] = mapped_column(String(100))
    exposure_date: Mapped[Optional[date]] = mapped_column(Date)
    last_contact_date: Mapped[Optional[date]] = mapped_column(Date)
    exposure_setting: Mapped[Optional[str]] = mapped_column(String(200))
    symptoms_developed: Mapped[bool] = mapped_column(Boolean, default=False)
    symptom_onset_date: Mapped[Optional[date]] = mapped_column(Date)
    tested: Mapped[bool] = mapped_column(Boolean, default=False)
    test_result: Mapped[Optional[str]] = mapped_column(String(50))
    monitoring_start_date: Mapped[Optional[date]] = mapped_column(Date)
    monitoring_end_date: Mapped[Optional[date]] = mapped_column(Date)
    monitoring_status: Mapped[str] = mapped_column(String(50), default="active")
    outcome: Mapped[Optional[str]] = mapped_column(String(100))
    traced_by: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    disease_case = orm_relationship("DiseaseCase", back_populates="contacts")
