import uuid
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    AppointmentStatus,
    AppointmentType,
    DayOfWeek,
    ReminderChannel,
    ReminderStatus,
)


# ─── Appointment ───────────────────────────────────────────────────────────────
class AppointmentCreate(BaseModel):
    patient_id: uuid.UUID
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    provider_id: Optional[uuid.UUID] = None
    provider_name: Optional[str] = None
    department: Optional[str] = None
    appointment_type: AppointmentType
    appointment_date: date
    start_time: time
    end_time: time
    duration_minutes: int = 30
    reason: Optional[str] = None
    notes: Optional[str] = None
    facility_id: Optional[str] = None
    location: Optional[str] = None
    language_preference: Optional[str] = "en"

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v, info):
        if info.data.get("start_time") and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class AppointmentUpdate(BaseModel):
    provider_id: Optional[uuid.UUID] = None
    provider_name: Optional[str] = None
    appointment_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[str] = None
    status: Optional[AppointmentStatus] = None


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    provider_id: Optional[uuid.UUID] = None
    provider_name: Optional[str] = None
    department: Optional[str] = None
    appointment_type: AppointmentType
    appointment_date: date
    start_time: time
    end_time: time
    duration_minutes: int
    status: AppointmentStatus
    reason: Optional[str] = None
    notes: Optional[str] = None
    facility_id: Optional[str] = None
    location: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    language_preference: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppointmentReschedule(BaseModel):
    appointment_date: date
    start_time: time
    end_time: time
    reason: Optional[str] = None


class AppointmentCancel(BaseModel):
    reason: Optional[str] = None


# ─── Schedule Template ─────────────────────────────────────────────────────────
class ScheduleTemplateCreate(BaseModel):
    provider_id: uuid.UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    slot_duration_minutes: int = 30
    max_patients: int = 20
    location: Optional[str] = None
    notes: Optional[str] = None


class ScheduleTemplateResponse(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    slot_duration_minutes: int
    max_patients: int
    is_active: bool
    location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Time Slot ─────────────────────────────────────────────────────────────────
class TimeSlotResponse(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    slot_date: date
    start_time: time
    end_time: time
    is_available: bool
    is_booked: bool

    model_config = ConfigDict(from_attributes=True)


# ─── Reminder ──────────────────────────────────────────────────────────────────
class ReminderCreate(BaseModel):
    appointment_id: uuid.UUID
    channel: ReminderChannel
    recipient: str
    message: str
    scheduled_for: datetime


class ReminderResponse(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    channel: ReminderChannel
    recipient: str
    message: str
    scheduled_for: datetime
    sent_at: Optional[datetime] = None
    status: ReminderStatus

    model_config = ConfigDict(from_attributes=True)


# ─── Waitlist ──────────────────────────────────────────────────────────────────
class WaitlistCreate(BaseModel):
    patient_id: uuid.UUID
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    provider_id: Optional[uuid.UUID] = None
    appointment_type: AppointmentType
    preferred_date_from: date
    preferred_date_to: date
    preferred_time: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class WaitlistResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    provider_id: Optional[uuid.UUID] = None
    appointment_type: AppointmentType
    preferred_date_from: date
    preferred_date_to: date
    preferred_time: Optional[str] = None
    reason: Optional[str] = None
    priority: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
