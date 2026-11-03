import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class JourneyPriority(str, Enum):
    emergency = "emergency"
    urgent = "urgent"
    routine = "routine"


class JourneyStatus(str, Enum):
    waiting = "waiting"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class PaymentScheme(str, Enum):
    """Billing scheme used for this visit.

    Stored as a string so hospitals can add schemes without a migration.
    """

    cash = "cash"
    nhima = "nhima"
    prudential = "prudential"
    sanlam = "sanlam"
    madison = "madison"
    jubilee = "jubilee"
    employer = "employer"
    other = "other"


class VisitType(str, Enum):
    new = "new"
    review = "review"


class VisitPaymentStatus(str, Enum):
    paid = "paid"
    unpaid = "unpaid"


class StepType(str, Enum):
    registration = "registration"
    triage = "triage"
    consultation = "consultation"
    laboratory = "laboratory"
    pharmacy = "pharmacy"
    imaging = "imaging"
    procedure = "procedure"
    admission = "admission"
    cashier = "cashier"
    referral = "referral"
    discharge = "discharge"
    other = "other"


class StepStatus(str, Enum):
    waiting = "waiting"
    called = "called"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"
    cancelled = "cancelled"


class StepOutcome(str, Enum):
    completed = "completed"
    referred = "referred"
    admitted = "admitted"
    discharged = "discharged"
    left_without_being_seen = "left_without_being_seen"
    no_show = "no_show"
    cancelled = "cancelled"


class FlowPatientSummary(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    nrc_number: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JourneyStepResponse(BaseModel):
    id: uuid.UUID
    journey_id: uuid.UUID
    step_number: int
    step_type: str
    service_point: str
    status: str
    priority: str
    outcome: Optional[str] = None

    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None

    queue_position: Optional[int] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

    referred_to_step_type: Optional[str] = None
    referred_to_service_point: Optional[str] = None
    referred_to_department_id: Optional[uuid.UUID] = None
    referred_to_provider_id: Optional[str] = None

    called_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JourneyResponse(BaseModel):
    id: uuid.UUID
    hospital_id: uuid.UUID
    patient_id: uuid.UUID
    encounter_id: Optional[uuid.UUID] = None
    journey_number: str
    status: str
    priority: str
    payment_scheme: str = PaymentScheme.cash.value
    visit_type: str = VisitType.new.value
    payment_status: str = VisitPaymentStatus.unpaid.value
    scheme_number: Optional[str] = None
    chief_complaint: Optional[str] = None
    arrival_notes: Optional[str] = None

    current_step_id: Optional[uuid.UUID] = None
    current_step_type: Optional[str] = None
    current_service_point: Optional[str] = None
    current_department_id: Optional[uuid.UUID] = None
    current_department_name: Optional[str] = None
    current_provider_id: Optional[str] = None
    current_provider_name: Optional[str] = None

    checked_in_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    closed_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    patient: Optional[FlowPatientSummary] = None

    model_config = ConfigDict(from_attributes=True)


class JourneyDetailResponse(JourneyResponse):
    steps: list[JourneyStepResponse] = Field(default_factory=list)


class JourneyCreate(BaseModel):
    patient_id: uuid.UUID
    encounter_id: Optional[uuid.UUID] = None
    priority: JourneyPriority = JourneyPriority.routine
    payment_scheme: PaymentScheme = PaymentScheme.cash
    visit_type: VisitType = VisitType.new
    payment_status: VisitPaymentStatus = VisitPaymentStatus.unpaid
    scheme_number: Optional[str] = Field(None, max_length=80)
    chief_complaint: Optional[str] = Field(None, max_length=2000)
    arrival_notes: Optional[str] = Field(None, max_length=5000)

    step_type: StepType = StepType.registration
    service_point: str = Field("registration", min_length=1, max_length=50)
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = Field(None, max_length=200)
    provider_id: Optional[str] = Field(None, max_length=50)
    provider_name: Optional[str] = Field(None, max_length=200)
    reason: Optional[str] = Field(None, max_length=2000)


class RouteRequest(BaseModel):
    """Send a patient onward to another doctor, counter, nurse or service point."""

    step_type: StepType
    service_point: str = Field(..., min_length=1, max_length=50)
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = Field(None, max_length=200)
    provider_id: Optional[str] = Field(None, max_length=50)
    provider_name: Optional[str] = Field(None, max_length=200)
    priority: Optional[JourneyPriority] = None
    reason: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=5000)
    outcome: StepOutcome = StepOutcome.referred


class CompleteStepRequest(BaseModel):
    outcome: StepOutcome = StepOutcome.completed
    notes: Optional[str] = Field(None, max_length=5000)


class SkipStepRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=2000)
    outcome: StepOutcome = StepOutcome.left_without_being_seen


class CloseJourneyRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=2000)
    outcome: StepOutcome = StepOutcome.discharged


class QueueItemResponse(BaseModel):
    step_id: uuid.UUID
    journey_id: uuid.UUID
    journey_number: str
    patient_id: uuid.UUID
    patient_name: str
    nrc_number: Optional[str] = None
    phone: Optional[str] = None

    priority: str
    status: str
    step_type: str
    service_point: str
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    provider_id: Optional[str] = None
    provider_name: Optional[str] = None

    payment_scheme: str = PaymentScheme.cash.value
    visit_type: str = VisitType.new.value
    payment_status: str = VisitPaymentStatus.unpaid.value
    scheme_number: Optional[str] = None

    position: int
    wait_minutes: int
    reason: Optional[str] = None
    checked_in_at: datetime
    created_at: datetime


class QueueResponse(BaseModel):
    items: list[QueueItemResponse]
    total: int


class FlowStatsResponse(BaseModel):
    waiting: int
    called: int
    in_progress: int
    active_total: int
    completed_today: int
    by_priority: dict[str, int]
    by_service_point: dict[str, int]
    average_wait_minutes: float
    longest_wait_minutes: int


class DestinationDepartment(BaseModel):
    id: uuid.UUID
    name: str
    code: Optional[str] = None
    location: Optional[str] = None


class DestinationStaff(BaseModel):
    id: uuid.UUID
    user_id: Optional[str] = None
    name: str
    role: str
    speciality: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None


class ServicePointOption(BaseModel):
    code: str
    label: str
    step_type: StepType


class DestinationsResponse(BaseModel):
    departments: list[DestinationDepartment]
    staff: list[DestinationStaff]
    service_points: list[ServicePointOption]
