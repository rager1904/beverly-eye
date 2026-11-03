from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, SoftDeleteMixin, TenantMixin


class CHWStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    on_leave = "on_leave"
    suspended = "suspended"
    terminated = "terminated"


class VisitStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    missed = "missed"
    cancelled = "cancelled"


class VaccinationStatus(str, enum.Enum):
    administered = "administered"
    missed = "missed"
    scheduled = "scheduled"
    contraindicated = "contraindicated"


class ReferralStatus(str, enum.Enum):
    initiated = "initiated"
    accepted = "accepted"
    completed = "completed"
    cancelled = "cancelled"


class EducationTopic(str, enum.Enum):
    malaria_prevention = "malaria_prevention"
    hiv_aids = "hiv_aids"
    tb_awareness = "tb_awareness"
    nutrition = "nutrition"
    maternal_health = "maternal_health"
    child_immunization = "child_immunization"
    family_planning = "family_planning"
    hygiene_sanitation = "hygiene_sanitation"
    covid19_prevention = "covid19_prevention"
    cholera_prevention = "cholera_prevention"
    diabetes = "diabetes"
    hypertension = "hypertension"


class CommunityHealthWorker(Base, AuditMixin, TenantMixin):
    __tablename__ = "community_health_workers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    nrc_number: Mapped[Optional[str]] = mapped_column(String(20))
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    catchment_area: Mapped[Optional[str]] = mapped_column(String(500))
    assigned_wards: Mapped[Optional[dict]] = mapped_column(Text)
    supervisor_id: Mapped[Optional[str]] = mapped_column(String(255))
    supervisor_name: Mapped[Optional[str]] = mapped_column(String(200))
    supervisor_phone: Mapped[Optional[str]] = mapped_column(String(20))
    skills: Mapped[Optional[dict]] = mapped_column(Text)
    languages: Mapped[Optional[dict]] = mapped_column(Text)
    status: Mapped[CHWStatus] = mapped_column(Enum(CHWStatus), default=CHWStatus.active)
    training_level: Mapped[Optional[str]] = mapped_column(String(100))
    training_completed_date: Mapped[Optional[date]] = mapped_column(Date)
    certification_number: Mapped[Optional[str]] = mapped_column(String(100))
    equipment_provided: Mapped[Optional[dict]] = mapped_column(Text)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_offline_capable: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    device_id: Mapped[Optional[str]] = mapped_column(String(200))

    visits = relationship("HouseholdVisit", back_populates="worker")
    vaccinations_administered = relationship("VaccinationRecord", back_populates="administered_by_worker")

    __table_args__ = (
        Index("idx_chw_district", "district", "status"),
        Index("idx_chw_supervisor", "supervisor_id"),
    )


class HouseholdVisit(Base, AuditMixin, TenantMixin):
    __tablename__ = "household_visits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("community_health_workers.id"), nullable=False, index=True
    )
    household_head: Mapped[str] = mapped_column(String(200), nullable=False)
    household_phone: Mapped[Optional[str]] = mapped_column(String(20))
    household_address: Mapped[Optional[str]] = mapped_column(String(500))
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    ward: Mapped[Optional[str]] = mapped_column(String(100))
    village: Mapped[Optional[str]] = mapped_column(String(100))
    location_lat: Mapped[Optional[float]] = mapped_column(Float)
    location_lng: Mapped[Optional[float]] = mapped_column(Float)
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[VisitStatus] = mapped_column(Enum(VisitStatus), default=VisitStatus.scheduled)
    household_size: Mapped[Optional[int]] = mapped_column(Integer)
    children_under_five: Mapped[Optional[int]] = mapped_column(Integer)
    pregnant_women: Mapped[Optional[int]] = mapped_column(Integer)
    findings: Mapped[Optional[str]] = mapped_column(Text)
    interventions: Mapped[Optional[str]] = mapped_column(Text)
    referrals_made: Mapped[Optional[dict]] = mapped_column(Text)
    health_education_provided: Mapped[Optional[dict]] = mapped_column(Text)
    water_source: Mapped[Optional[str]] = mapped_column(String(100))
    sanitation_type: Mapped[Optional[str]] = mapped_column(String(100))
    has_mosquito_net: Mapped[Optional[bool]] = mapped_column(Boolean)
    has_handwashing_facility: Mapped[Optional[bool]] = mapped_column(Boolean)
    malnutrition_screening: Mapped[Optional[str]] = mapped_column(String(50))
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_offline_created: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    worker = relationship("CommunityHealthWorker", back_populates="visits")

    __table_args__ = (
        Index("idx_hh_visit_worker", "worker_id", "visit_date"),
        Index("idx_hh_visit_district", "district", "visit_date"),
        Index("idx_hh_visit_followup", "follow_up_required", "follow_up_date"),
    )


class VaccinationRecord(Base, AuditMixin, TenantMixin):
    __tablename__ = "vaccination_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_name: Mapped[str] = mapped_column(String(200), nullable=False)
    child_date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    child_gender: Mapped[Optional[str]] = mapped_column(String(20))
    mother_name: Mapped[Optional[str]] = mapped_column(String(200))
    mother_nrc: Mapped[Optional[str]] = mapped_column(String(20))
    mother_phone: Mapped[Optional[str]] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(String(500))
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    vaccine_type: Mapped[str] = mapped_column(String(100), nullable=False)
    dose_number: Mapped[int] = mapped_column(Integer, nullable=False)
    total_doses: Mapped[Optional[int]] = mapped_column(Integer)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100))
    administered_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date)
    administered_by_worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("community_health_workers.id")
    )
    administered_by_name: Mapped[Optional[str]] = mapped_column(String(200))
    facility_name: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[VaccinationStatus] = mapped_column(Enum(VaccinationStatus), default=VaccinationStatus.administered)
    adverse_reaction: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_offline_created: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    administered_by_worker = relationship("CommunityHealthWorker", back_populates="vaccinations_administered")

    __table_args__ = (
        Index("idx_vaccination_child", "child_name", "vaccine_type"),
        Index("idx_vaccination_district", "district", "vaccine_type"),
        Index("idx_vaccination_date", "administered_date"),
    )


class MaternalHealthVisit(Base, AuditMixin, TenantMixin):
    __tablename__ = "maternal_health_visits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mother_name: Mapped[str] = mapped_column(String(200), nullable=False)
    mother_nrc: Mapped[Optional[str]] = mapped_column(String(20))
    mother_phone: Mapped[Optional[str]] = mapped_column(String(20))
    mother_age: Mapped[Optional[int]] = mapped_column(Integer)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    address: Mapped[Optional[str]] = mapped_column(String(500))
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    visit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    gestational_age_weeks: Mapped[Optional[int]] = mapped_column(Integer)
    gravida: Mapped[Optional[int]] = mapped_column(Integer)
    para: Mapped[Optional[int]] = mapped_column(Integer)
    blood_pressure_systolic: Mapped[Optional[int]] = mapped_column(Integer)
    blood_pressure_diastolic: Mapped[Optional[int]] = mapped_column(Integer)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float)
    hemoglobin: Mapped[Optional[float]] = mapped_column(Float)
    hiv_status: Mapped[Optional[str]] = mapped_column(String(50))
    on_art: Mapped[Optional[bool]] = mapped_column(Boolean)
    malaria_prophylaxis: Mapped[Optional[bool]] = mapped_column(Boolean)
    iron_supplementation: Mapped[Optional[bool]] = mapped_column(Boolean)
    tetanus_vaccination: Mapped[Optional[str]] = mapped_column(String(50))
    danger_signs: Mapped[Optional[str]] = mapped_column(Text)
    findings: Mapped[Optional[str]] = mapped_column(Text)
    interventions: Mapped[Optional[str]] = mapped_column(Text)
    referred: Mapped[bool] = mapped_column(Boolean, default=False)
    referred_to: Mapped[Optional[str]] = mapped_column(String(200))
    referral_reason: Mapped[Optional[str]] = mapped_column(Text)
    next_visit_date: Mapped[Optional[date]] = mapped_column(Date)
    conducted_by: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_offline_created: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_maternal_mother", "mother_name"),
        Index("idx_maternal_district", "district", "visit_type"),
        Index("idx_maternal_visit_date", "visit_date"),
    )


class HealthEducation(Base, AuditMixin, TenantMixin):
    __tablename__ = "health_education"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic: Mapped[EducationTopic] = mapped_column(Enum(EducationTopic), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    ward: Mapped[Optional[str]] = mapped_column(String(100))
    village: Mapped[Optional[str]] = mapped_column(String(100))
    facilitator_name: Mapped[str] = mapped_column(String(200), nullable=False)
    facilitator_id: Mapped[Optional[str]] = mapped_column(String(255))
    participants_count: Mapped[int] = mapped_column(Integer, default=0)
    male_participants: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    female_participants: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    child_participants: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    key_messages: Mapped[Optional[str]] = mapped_column(Text)
    materials_used: Mapped[Optional[dict]] = mapped_column(Text)
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    follow_up_planned: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_offline_created: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_health_education_topic", "topic", "session_date"),
        Index("idx_health_education_location", "district", "facilitator_name"),
    )
