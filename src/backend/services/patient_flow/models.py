import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, TenantMixin


class PatientJourney(Base, AuditMixin, TenantMixin):
    """One patient visit, from arrival to discharge/closure.

    ``status``, ``priority`` and the ``current_*`` fields are stored as
    strings so that new workflow states can be introduced without a
    database enum migration. Validation lives in :mod:`schemas`.
    """

    __tablename__ = "patient_journeys"
    # Fetch database-generated audit timestamps during awaited flushes so
    # FastAPI can serialize them without triggering asynchronous lazy loads.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True
    )
    # Kept as a plain UUID because the legacy migration schema and the
    # SQLAlchemy models disagree about the encounters table.
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    journey_number: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), default="waiting", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="routine", index=True)

    # Registration / billing details captured at the counter for this visit.
    payment_scheme: Mapped[str] = mapped_column(String(50), default="cash", index=True)
    visit_type: Mapped[str] = mapped_column(String(20), default="new", index=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="unpaid", index=True)
    scheme_number: Mapped[Optional[str]] = mapped_column(String(80))

    chief_complaint: Mapped[Optional[str]] = mapped_column(Text)
    arrival_notes: Mapped[Optional[str]] = mapped_column(Text)

    current_step_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    current_step_type: Mapped[Optional[str]] = mapped_column(String(30))
    current_service_point: Mapped[Optional[str]] = mapped_column(String(50))
    current_department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    current_department_name: Mapped[Optional[str]] = mapped_column(String(200))
    current_provider_id: Mapped[Optional[str]] = mapped_column(String(50))
    current_provider_name: Mapped[Optional[str]] = mapped_column(String(200))

    checked_in_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    closed_reason: Mapped[Optional[str]] = mapped_column(Text)

    steps = relationship(
        "JourneyStep",
        back_populates="journey",
        cascade="all, delete-orphan",
        order_by="JourneyStep.step_number",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "hospital_id", "journey_number", name="uq_patient_journeys_hospital_number"
        ),
        Index("idx_patient_journeys_patient", "patient_id", "checked_in_at"),
        Index("idx_patient_journeys_hospital_status", "hospital_id", "status"),
        Index("idx_patient_journeys_hospital_priority", "hospital_id", "priority"),
    )


class JourneyStep(Base, AuditMixin, TenantMixin):
    """A single service-point visit / queue ticket inside a journey."""

    __tablename__ = "journey_steps"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patient_journeys.id"), index=True
    )
    step_number: Mapped[int] = mapped_column(Integer)

    step_type: Mapped[str] = mapped_column(String(30), index=True)
    service_point: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), default="waiting", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="routine", index=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(30))

    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    department_name: Mapped[Optional[str]] = mapped_column(String(200))
    provider_id: Mapped[Optional[str]] = mapped_column(String(50))
    provider_name: Mapped[Optional[str]] = mapped_column(String(200))

    queue_position: Mapped[Optional[int]] = mapped_column(Integer)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    referred_to_step_type: Mapped[Optional[str]] = mapped_column(String(30))
    referred_to_service_point: Mapped[Optional[str]] = mapped_column(String(50))
    referred_to_department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True)
    )
    referred_to_provider_id: Mapped[Optional[str]] = mapped_column(String(50))

    called_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    journey = relationship("PatientJourney", back_populates="steps")

    __table_args__ = (
        UniqueConstraint(
            "journey_id", "step_number", name="uq_journey_steps_journey_number"
        ),
        Index("idx_journey_steps_hospital_status", "hospital_id", "status"),
        Index(
            "idx_journey_steps_queue",
            "hospital_id",
            "service_point",
            "status",
            "priority",
        ),
        Index("idx_journey_steps_provider", "hospital_id", "provider_id", "status"),
    )
