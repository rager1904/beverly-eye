import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, TenantMixin


class ConsultationStatus(str, enum.Enum):
    scheduled = "scheduled"
    in_waiting_room = "in_waiting_room"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class ConsultationType(str, enum.Enum):
    video = "video"
    audio = "audio"
    chat = "chat"
    phone = "phone"


class RecordingStatus(str, enum.Enum):
    recording = "recording"
    completed = "completed"
    failed = "failed"
    deleted = "deleted"


class PrescriptionStatus(str, enum.Enum):
    draft = "draft"
    signed = "signed"
    dispensed = "dispensed"
    cancelled = "cancelled"


class Teleconsultation(Base, AuditMixin, TenantMixin):
    __tablename__ = "teleconsultations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    appointment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    consultation_type: Mapped[ConsultationType] = mapped_column(Enum(ConsultationType))
    status: Mapped[ConsultationStatus] = mapped_column(
        Enum(ConsultationStatus), default=ConsultationStatus.scheduled
    )
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    diagnosis: Mapped[Optional[str]] = mapped_column(Text)
    treatment_plan: Mapped[Optional[str]] = mapped_column(Text)
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    feedback: Mapped[Optional[str]] = mapped_column(Text)

    recordings = relationship("Recording", back_populates="consultation")
    prescriptions = relationship("Prescription", back_populates="consultation")

    __table_args__ = (
        Index("idx_teleconsult_provider_status", "provider_id", "status"),
        Index("idx_teleconsult_patient", "patient_id", "scheduled_start"),
    )


class WaitingRoom(Base, AuditMixin, TenantMixin):
    __tablename__ = "waiting_rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teleconsultations.id"), unique=True
    )
    patient_joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    provider_joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    session_token: Mapped[Optional[str]] = mapped_column(String(500))
    room_sid: Mapped[Optional[str]] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Recording(Base, TenantMixin):
    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teleconsultations.id"), index=True
    )
    recording_type: Mapped[str] = mapped_column(String(50))
    file_url: Mapped[Optional[str]] = mapped_column(String(1000))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus), default=RecordingStatus.recording
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    consultation = relationship("Teleconsultation", back_populates="recordings")


class Prescription(Base, AuditMixin, TenantMixin):
    __tablename__ = "telemedicine_prescriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teleconsultations.id"), index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    medication_name: Mapped[str] = mapped_column(String(300))
    generic_name: Mapped[Optional[str]] = mapped_column(String(300))
    dosage: Mapped[str] = mapped_column(String(100))
    frequency: Mapped[str] = mapped_column(String(200))
    duration: Mapped[str] = mapped_column(String(100))
    route: Mapped[Optional[str]] = mapped_column(String(50))
    quantity: Mapped[Optional[str]] = mapped_column(String(50))
    refills: Mapped[int] = mapped_column(Integer, default=0)
    instructions: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[PrescriptionStatus] = mapped_column(
        Enum(PrescriptionStatus), default=PrescriptionStatus.draft
    )
    signed_by: Mapped[Optional[str]] = mapped_column(String(200))
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    dispensed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    pharmacy_notes: Mapped[Optional[str]] = mapped_column(Text)
    is_controlled: Mapped[bool] = mapped_column(Boolean, default=False)

    consultation = relationship("Teleconsultation", back_populates="prescriptions")
