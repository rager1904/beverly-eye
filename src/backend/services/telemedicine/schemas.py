import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import ConsultationStatus, ConsultationType, PrescriptionStatus, RecordingStatus


class ConsultationCreate(BaseModel):
    patient_id: uuid.UUID
    provider_id: Optional[uuid.UUID] = None
    appointment_id: Optional[uuid.UUID] = None
    consultation_type: ConsultationType
    scheduled_start: Optional[datetime] = None
    chief_complaint: Optional[str] = None


class ConsultationResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None
    consultation_type: ConsultationType
    status: ConsultationStatus
    scheduled_start: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    chief_complaint: Optional[str] = None
    notes: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    encounter_id: Optional[uuid.UUID] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsultationCreatedResponse(BaseModel):
    consultation: ConsultationResponse
    invite_token: str
    ice_servers: list[dict]


class InviteJoinResponse(BaseModel):
    consultation_id: uuid.UUID
    status: ConsultationStatus
    consultation_type: ConsultationType
    ice_servers: list[dict]


class SignalCreate(BaseModel):
    type: str = Field(..., pattern="^(offer|answer|ice_candidate|chat|hangup)$")
    payload: dict


class SignalEnvelope(BaseModel):
    type: str
    sender_role: str
    payload: dict
    sent_at: datetime


class SignalBatch(BaseModel):
    items: list[SignalEnvelope]
    next_cursor: int


class InviteTokenResponse(BaseModel):
    invite_token: str
    expires_at: datetime


class ConsultationComplete(BaseModel):
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    notes: Optional[str] = None
    encounter_id: Optional[uuid.UUID] = None


class ConsultationCancel(BaseModel):
    reason: Optional[str] = None


class WaitingRoomResponse(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    patient_joined_at: Optional[datetime] = None
    provider_joined_at: Optional[datetime] = None
    room_sid: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RecordingCreate(BaseModel):
    recording_type: str
    file_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[int] = None
    notes: Optional[str] = None


class RecordingResponse(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    recording_type: str
    file_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[int] = None
    status: RecordingStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PrescriptionCreate(BaseModel):
    consultation_id: uuid.UUID
    patient_id: uuid.UUID
    medication_name: str
    generic_name: Optional[str] = None
    dosage: str
    frequency: str
    duration: str
    route: Optional[str] = None
    quantity: Optional[str] = None
    refills: int = 0
    instructions: Optional[str] = None
    is_controlled: bool = False
    pharmacy_notes: Optional[str] = None


class PrescriptionResponse(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    patient_id: uuid.UUID
    medication_name: str
    generic_name: Optional[str] = None
    dosage: str
    frequency: str
    duration: str
    route: Optional[str] = None
    quantity: Optional[str] = None
    refills: int
    instructions: Optional[str] = None
    status: PrescriptionStatus
    signed_by: Optional[str] = None
    signed_at: Optional[datetime] = None
    is_controlled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
