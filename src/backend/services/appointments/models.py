import enum
import uuid
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, TenantMixin


class AppointmentType(str, enum.Enum):
    general = "general"
    follow_up = "follow_up"
    emergency = "emergency"
    specialist = "specialist"
    maternity = "maternity"
    immunization = "immunization"
    lab = "lab"
    imaging = "imaging"
    telemedicine = "telemedicine"
    home_visit = "home_visit"
    antenatal = "antenatal"
    postnatal = "postnatal"
    hiv = "hiv"
    tb = "tb"
    mental_health = "mental_health"


class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    checked_in = "checked_in"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"
    rescheduled = "rescheduled"


class DayOfWeek(str, enum.Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"


class ReminderChannel(str, enum.Enum):
    sms = "sms"
    email = "email"
    whatsapp = "whatsapp"
    call = "call"
    push = "push"


class ReminderStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class Appointment(Base, AuditMixin, TenantMixin):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    patient_name: Mapped[Optional[str]] = mapped_column(String(200))
    patient_phone: Mapped[Optional[str]] = mapped_column(String(20))
    provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    provider_name: Mapped[Optional[str]] = mapped_column(String(200))
    department: Mapped[Optional[str]] = mapped_column(String(100))
    appointment_type: Mapped[AppointmentType] = mapped_column(Enum(AppointmentType))
    appointment_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.scheduled
    )
    reason: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    facility_id: Mapped[Optional[str]] = mapped_column(String(50))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text)
    language_preference: Mapped[Optional[str]] = mapped_column(String(10), default="en")

    reminders = relationship("Reminder", back_populates="appointment")

    __table_args__ = (
        Index("idx_appt_date", "appointment_date", "hospital_id"),
        Index("idx_appt_provider_date", "provider_id", "appointment_date"),
        Index("idx_appt_patient", "patient_id", "status"),
    )


class ScheduleTemplate(Base, AuditMixin, TenantMixin):
    __tablename__ = "schedule_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )
    day_of_week: Mapped[DayOfWeek] = mapped_column(Enum(DayOfWeek))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    max_patients: Mapped[int] = mapped_column(Integer, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    location: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("provider_id", "day_of_week", name="uq_provider_day"),
    )


class TimeSlot(Base, AuditMixin, TenantMixin):
    __tablename__ = "time_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    slot_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False)
    appointment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    __table_args__ = (
        UniqueConstraint("provider_id", "slot_date", "start_time", name="uq_slot"),
        Index("idx_slot_date_available", "slot_date", "is_available"),
    )


class Reminder(Base, AuditMixin, TenantMixin):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id"), index=True
    )
    channel: Mapped[ReminderChannel] = mapped_column(Enum(ReminderChannel))
    recipient: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus), default=ReminderStatus.pending
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    appointment = relationship("Appointment", back_populates="reminders")


class Waitlist(Base, AuditMixin, TenantMixin):
    __tablename__ = "waitlist"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    patient_name: Mapped[Optional[str]] = mapped_column(String(200))
    patient_phone: Mapped[Optional[str]] = mapped_column(String(20))
    provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    appointment_type: Mapped[AppointmentType] = mapped_column(Enum(AppointmentType))
    preferred_date_from: Mapped[date] = mapped_column(Date)
    preferred_date_to: Mapped[date] = mapped_column(Date)
    preferred_time: Mapped[Optional[str]] = mapped_column(String(50))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    converted_appointment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
