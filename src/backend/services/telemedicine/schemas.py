import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import ConsultationStatus, ConsultationType, PrescriptionStatus, RecordingStatus


class ConsultationCreate(BaseModel):
    patient_id: uuid.UUID
    provider_id: uuid.UUID
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
    session_token: Optional[str] = None
    room_sid: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    room_sid: str
    token_type: str = "temporary"
    expires_in: int = 3600
    identity_patient: str
    identity_provider: str


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


class SignalMessage(BaseModel):
    type: str = Field(..., pattern="^(offer|answer|ice_candidate)$")
    room: str
    identity: str
    sdp: Optional[str] = None
    candidate: Optional[str] = None
    sdpMid: Optional[str] = None
    sdpMLineIndex: Optional[int] = None
