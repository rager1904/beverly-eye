import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.services.emr.models import Patient
from src.backend.services.hospital_management.models import (
    Department,
    Staff,
    StaffRole,
)

from . import models, schemas

logger = logging.getLogger(__name__)

ACTIVE_STEP_STATUSES = {
    schemas.StepStatus.waiting.value,
    schemas.StepStatus.called.value,
    schemas.StepStatus.in_progress.value,
}

PRIORITY_RANK = {
    schemas.JourneyPriority.emergency.value: 0,
    schemas.JourneyPriority.urgent.value: 1,
    schemas.JourneyPriority.routine.value: 2,
}

# Allowed step state transitions. Keeping this table pure makes the workflow
# easy to test and extend without touching the database schema.
STEP_TRANSITIONS: dict[str, set[str]] = {
    schemas.StepStatus.waiting.value: {
        schemas.StepStatus.called.value,
        schemas.StepStatus.in_progress.value,
        schemas.StepStatus.completed.value,
        schemas.StepStatus.skipped.value,
        schemas.StepStatus.cancelled.value,
    },
    schemas.StepStatus.called.value: {
        schemas.StepStatus.in_progress.value,
        schemas.StepStatus.completed.value,
        schemas.StepStatus.skipped.value,
        schemas.StepStatus.cancelled.value,
    },
    schemas.StepStatus.in_progress.value: {
        schemas.StepStatus.completed.value,
        schemas.StepStatus.skipped.value,
        schemas.StepStatus.cancelled.value,
    },
    schemas.StepStatus.completed.value: set(),
    schemas.StepStatus.skipped.value: set(),
    schemas.StepStatus.cancelled.value: set(),
}

DESTINATION_STAFF_ROLES = [
    StaffRole.doctor,
    StaffRole.nurse,
    StaffRole.midwife,
    StaffRole.clinical_officer,
]

SERVICE_POINTS = [
    schemas.ServicePointOption(
        code="registration",
        label="Registration / Counter",
        step_type=schemas.StepType.registration,
    ),
    schemas.ServicePointOption(
        code="triage", label="Triage / Nurse Station", step_type=schemas.StepType.triage
    ),
    schemas.ServicePointOption(
        code="general",
        label="General Clinic",
        step_type=schemas.StepType.consultation,
    ),
    schemas.ServicePointOption(
        code="eye",
        label="Eye Clinic",
        step_type=schemas.StepType.consultation,
    ),
    schemas.ServicePointOption(
        code="dental",
        label="Dental Clinic",
        step_type=schemas.StepType.consultation,
    ),
    schemas.ServicePointOption(
        code="laboratory", label="Laboratory", step_type=schemas.StepType.laboratory
    ),
    schemas.ServicePointOption(
        code="pharmacy", label="Pharmacy", step_type=schemas.StepType.pharmacy
    ),
    schemas.ServicePointOption(
        code="imaging", label="Imaging / Radiology", step_type=schemas.StepType.imaging
    ),
    schemas.ServicePointOption(
        code="procedure", label="Procedure Room", step_type=schemas.StepType.procedure
    ),
    schemas.ServicePointOption(
        code="cashier", label="Cashier / Billing", step_type=schemas.StepType.cashier
    ),
    schemas.ServicePointOption(
        code="admission", label="Ward / Admission", step_type=schemas.StepType.admission
    ),
    schemas.ServicePointOption(
        code="referral", label="Referral Desk", step_type=schemas.StepType.referral
    ),
    schemas.ServicePointOption(
        code="discharge", label="Discharge Desk", step_type=schemas.StepType.discharge
    ),
]


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def can_transition_step(current: str, target: str) -> bool:
    """Return whether a step may move from ``current`` to ``target``."""
    return _enum_value(target) in STEP_TRANSITIONS.get(_enum_value(current), set())


def build_journey_number(now: Optional[datetime] = None) -> str:
    """Human-readable, collision-resistant journey/visit number."""
    moment = now or datetime.utcnow()
    return f"PF-{moment:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


def calculate_wait_minutes(
    started_at: datetime, finished_at: Optional[datetime] = None
) -> int:
    """Whole minutes waited between arrival and service/completion."""
    end = finished_at or datetime.utcnow()
    seconds = (end - started_at).total_seconds()
    return max(0, int(seconds // 60))


def priority_sort_key(priority: str) -> int:
    return PRIORITY_RANK.get(_enum_value(priority), PRIORITY_RANK["routine"])


class JourneyService:
    """Coordinates patient journeys, queue steps and onward referrals."""

    def __init__(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
    ):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id
        self.user_name = user_name

    # ------------------------------------------------------------------
    # Patient helpers
    # ------------------------------------------------------------------
    async def _get_patient_summary(
        self, patient_id: uuid.UUID
    ) -> Optional[schemas.FlowPatientSummary]:
        # Select explicit legacy-safe columns: the repository contains two
        # different patient schemas (migration vs ORM), and both share these.
        result = await self.db.execute(
            select(
                Patient.id,
                Patient.first_name,
                Patient.last_name,
                Patient.nrc_number,
                Patient.phone,
            ).where(Patient.id == patient_id)
        )
        row = result.first()
        if row is None:
            return None
        return schemas.FlowPatientSummary(
            id=row[0],
            first_name=row[1],
            last_name=row[2],
            nrc_number=row[3],
            phone=row[4],
        )

    async def _attach_patient(self, journey: models.PatientJourney) -> None:
        journey.patient = await self._get_patient_summary(journey.patient_id)

    # ------------------------------------------------------------------
    # Journey lifecycle
    # ------------------------------------------------------------------
    async def create_journey(self, data: schemas.JourneyCreate) -> models.PatientJourney:
        patient = await self._get_patient_summary(data.patient_id)
        if patient is None:
            raise LookupError("Patient not found")

        now = datetime.utcnow()
        journey = models.PatientJourney(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            patient_id=data.patient_id,
            encounter_id=data.encounter_id,
            journey_number=build_journey_number(now),
            status=schemas.JourneyStatus.waiting.value,
            priority=data.priority.value,
            payment_scheme=data.payment_scheme.value,
            visit_type=data.visit_type.value,
            payment_status=data.payment_status.value,
            scheme_number=data.scheme_number,
            chief_complaint=data.chief_complaint,
            arrival_notes=data.arrival_notes,
            current_step_type=data.step_type.value,
            current_service_point=data.service_point,
            current_department_id=data.department_id,
            current_department_name=data.department_name,
            current_provider_id=data.provider_id,
            current_provider_name=data.provider_name,
            checked_in_at=now,
            created_by=self.user_id,
            updated_by=self.user_id,
            # Keep the new collection loaded across flushes. Accessing an
            # uninitialized relationship after flush triggers implicit SQL,
            # which AsyncSession cannot await from attribute access.
            steps=[],
        )
        self.db.add(journey)
        await self.db.flush()

        step = models.JourneyStep(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            journey_id=journey.id,
            step_number=1,
            step_type=data.step_type.value,
            service_point=data.service_point,
            status=schemas.StepStatus.waiting.value,
            priority=data.priority.value,
            department_id=data.department_id,
            department_name=data.department_name,
            provider_id=data.provider_id,
            provider_name=data.provider_name,
            reason=data.reason,
            created_by=self.user_id,
            updated_by=self.user_id,
        )
        self.db.add(step)
        await self.db.flush()

        journey.current_step_id = step.id
        journey.steps.append(step)
        journey.patient = patient
        await self.db.flush()

        logger.info(
            "Patient journey started",
            extra={
                "journey_id": str(journey.id),
                "journey_number": journey.journey_number,
                "patient_id": str(journey.patient_id),
                "hospital_id": str(self.hospital_id),
                "service_point": step.service_point,
            },
        )
        return journey

    async def get_journey(
        self, journey_id: uuid.UUID
    ) -> Optional[models.PatientJourney]:
        result = await self.db.execute(
            select(models.PatientJourney)
            .where(
                models.PatientJourney.id == journey_id,
                models.PatientJourney.hospital_id == self.hospital_id,
            )
            .options(selectinload(models.PatientJourney.steps))
        )
        journey = result.scalar_one_or_none()
        if journey is not None:
            await self._attach_patient(journey)
        return journey

    async def get_patient_journeys(
        self, patient_id: uuid.UUID, limit: int = 20
    ) -> list[models.PatientJourney]:
        result = await self.db.execute(
            select(models.PatientJourney)
            .where(
                models.PatientJourney.patient_id == patient_id,
                models.PatientJourney.hospital_id == self.hospital_id,
            )
            .order_by(models.PatientJourney.checked_in_at.desc())
            .limit(limit)
            .options(selectinload(models.PatientJourney.steps))
        )
        journeys = list(result.scalars().all())
        patient = await self._get_patient_summary(patient_id)
        for journey in journeys:
            journey.patient = patient
        return journeys

    async def route_patient(
        self, journey_id: uuid.UUID, data: schemas.RouteRequest
    ) -> models.PatientJourney:
        """Complete the current step and queue the patient at the next one."""
        journey = await self.get_journey(journey_id)
        if journey is None:
            raise LookupError("Journey not found")
        if journey.status in (
            schemas.JourneyStatus.completed.value,
            schemas.JourneyStatus.cancelled.value,
        ):
            raise ValueError("Cannot route a closed journey")

        now = datetime.utcnow()
        current = self._find_current_step(journey)
        if current is not None and current.status in ACTIVE_STEP_STATUSES:
            self._transition_step(current, schemas.StepStatus.completed.value)
            current.outcome = data.outcome.value
            current.completed_at = now
            current.notes = data.notes or current.notes
            current.referred_to_step_type = data.step_type.value
            current.referred_to_service_point = data.service_point
            current.referred_to_department_id = data.department_id
            current.referred_to_provider_id = data.provider_id
            current.updated_by = self.user_id

        next_number = max((s.step_number for s in journey.steps), default=0) + 1
        priority = data.priority.value if data.priority else journey.priority
        step = models.JourneyStep(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            journey_id=journey.id,
            step_number=next_number,
            step_type=data.step_type.value,
            service_point=data.service_point,
            status=schemas.StepStatus.waiting.value,
            priority=priority,
            department_id=data.department_id,
            department_name=data.department_name,
            provider_id=data.provider_id,
            provider_name=data.provider_name,
            reason=data.reason,
            notes=data.notes,
            created_by=self.user_id,
            updated_by=self.user_id,
        )
        self.db.add(step)
        await self.db.flush()

        journey.steps.append(step)
        journey.current_step_id = step.id
        journey.current_step_type = step.step_type
        journey.current_service_point = step.service_point
        journey.current_department_id = step.department_id
        journey.current_department_name = step.department_name
        journey.current_provider_id = step.provider_id
        journey.current_provider_name = step.provider_name
        journey.status = schemas.JourneyStatus.waiting.value
        journey.started_at = journey.started_at or now
        journey.updated_by = self.user_id
        await self.db.flush()

        logger.info(
            "Patient routed",
            extra={
                "journey_id": str(journey.id),
                "from_service_point": current.service_point if current else None,
                "to_service_point": step.service_point,
                "to_provider": step.provider_id,
            },
        )
        return journey

    async def call_step(
        self, journey_id: uuid.UUID, step_id: uuid.UUID
    ) -> models.PatientJourney:
        journey = await self._journey_with_step(journey_id, step_id)
        step = self._find_step(journey, step_id)
        if step.status != schemas.StepStatus.called.value:
            self._transition_step(step, schemas.StepStatus.called.value)
            step.called_at = datetime.utcnow()
        self._make_current(journey, step)
        journey.status = schemas.JourneyStatus.in_progress.value
        journey.updated_by = self.user_id
        await self.db.flush()
        return journey

    async def start_step(
        self, journey_id: uuid.UUID, step_id: uuid.UUID
    ) -> models.PatientJourney:
        journey = await self._journey_with_step(journey_id, step_id)
        step = self._find_step(journey, step_id)
        if step.status != schemas.StepStatus.in_progress.value:
            self._transition_step(step, schemas.StepStatus.in_progress.value)
            step.started_at = step.started_at or datetime.utcnow()
        self._make_current(journey, step)
        journey.status = schemas.JourneyStatus.in_progress.value
        journey.started_at = journey.started_at or datetime.utcnow()
        journey.updated_by = self.user_id
        await self.db.flush()
        return journey

    async def complete_step(
        self,
        journey_id: uuid.UUID,
        step_id: uuid.UUID,
        data: schemas.CompleteStepRequest,
    ) -> models.PatientJourney:
        journey = await self._journey_with_step(journey_id, step_id)
        step = self._find_step(journey, step_id)
        self._finish_step(step, data.outcome.value, data.notes)
        self._clear_current_if_matches(journey, step)
        journey.status = schemas.JourneyStatus.waiting.value
        journey.updated_by = self.user_id
        await self.db.flush()
        return journey

    async def skip_step(
        self,
        journey_id: uuid.UUID,
        step_id: uuid.UUID,
        data: schemas.SkipStepRequest,
    ) -> models.PatientJourney:
        journey = await self._journey_with_step(journey_id, step_id)
        step = self._find_step(journey, step_id)
        self._finish_step(
            step,
            data.outcome.value,
            data.reason,
            status=schemas.StepStatus.skipped.value,
        )
        self._clear_current_if_matches(journey, step)
        journey.status = schemas.JourneyStatus.waiting.value
        journey.updated_by = self.user_id
        await self.db.flush()
        return journey

    async def close_journey(
        self, journey_id: uuid.UUID, data: schemas.CloseJourneyRequest
    ) -> models.PatientJourney:
        journey = await self.get_journey(journey_id)
        if journey is None:
            raise LookupError("Journey not found")
        if journey.status == schemas.JourneyStatus.completed.value:
            return journey

        now = datetime.utcnow()
        current = self._find_current_step(journey)
        if current is not None and current.status in ACTIVE_STEP_STATUSES:
            self._finish_step(current, data.outcome.value, data.reason)

        cancelled = data.outcome == schemas.StepOutcome.cancelled
        journey.status = (
            schemas.JourneyStatus.cancelled.value
            if cancelled
            else schemas.JourneyStatus.completed.value
        )
        journey.completed_at = now
        journey.closed_reason = data.reason
        journey.current_step_id = None
        journey.current_step_type = None
        journey.current_service_point = None
        journey.current_department_id = None
        journey.current_department_name = None
        journey.current_provider_id = None
        journey.current_provider_name = None
        journey.updated_by = self.user_id
        await self.db.flush()
        return journey

    # ------------------------------------------------------------------
    # Queue and reporting
    # ------------------------------------------------------------------
    async def get_queue(
        self,
        service_point: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        provider_id: Optional[str] = None,
        step_type: Optional[str] = None,
        status: Optional[schemas.StepStatus] = None,
        include_completed: bool = False,
    ) -> schemas.QueueResponse:
        priority_order = case(
            (
                models.JourneyStep.priority
                == schemas.JourneyPriority.emergency.value,
                0,
            ),
            (
                models.JourneyStep.priority == schemas.JourneyPriority.urgent.value,
                1,
            ),
            else_=2,
        )

        stmt = (
            select(
                models.JourneyStep,
                models.PatientJourney,
                Patient.id,
                Patient.first_name,
                Patient.last_name,
                Patient.nrc_number,
                Patient.phone,
            )
            .join(
                models.PatientJourney,
                models.JourneyStep.journey_id == models.PatientJourney.id,
            )
            .join(Patient, models.PatientJourney.patient_id == Patient.id)
            .where(
                models.JourneyStep.hospital_id == self.hospital_id,
                models.PatientJourney.status.notin_(
                    [
                        schemas.JourneyStatus.completed.value,
                        schemas.JourneyStatus.cancelled.value,
                    ]
                ),
            )
        )

        if status is not None:
            stmt = stmt.where(models.JourneyStep.status == status.value)
        elif not include_completed:
            stmt = stmt.where(models.JourneyStep.status.in_(ACTIVE_STEP_STATUSES))

        if service_point:
            stmt = stmt.where(models.JourneyStep.service_point == service_point)
        if department_id:
            stmt = stmt.where(models.JourneyStep.department_id == department_id)
        if provider_id:
            stmt = stmt.where(models.JourneyStep.provider_id == provider_id)
        if step_type:
            stmt = stmt.where(models.JourneyStep.step_type == step_type)

        stmt = stmt.order_by(priority_order, models.JourneyStep.created_at)
        result = await self.db.execute(stmt)
        rows = result.all()

        items: list[schemas.QueueItemResponse] = []
        for position, row in enumerate(rows, start=1):
            step, journey, patient_id, first_name, last_name, nrc, phone = row
            items.append(
                schemas.QueueItemResponse(
                    step_id=step.id,
                    journey_id=journey.id,
                    journey_number=journey.journey_number,
                    patient_id=patient_id,
                    patient_name=f"{first_name} {last_name}".strip(),
                    nrc_number=nrc,
                    phone=phone,
                    priority=step.priority,
                    status=step.status,
                    step_type=step.step_type,
                    service_point=step.service_point,
                    department_id=step.department_id,
                    department_name=step.department_name,
                    provider_id=step.provider_id,
                    provider_name=step.provider_name,
                    payment_scheme=journey.payment_scheme,
                    visit_type=journey.visit_type,
                    payment_status=journey.payment_status,
                    scheme_number=journey.scheme_number,
                    position=position,
                    wait_minutes=calculate_wait_minutes(step.created_at),
                    reason=step.reason,
                    checked_in_at=journey.checked_in_at,
                    created_at=step.created_at,
                )
            )
        return schemas.QueueResponse(items=items, total=len(items))

    async def get_stats(self) -> schemas.FlowStatsResponse:
        active_result = await self.db.execute(
            select(models.JourneyStep).where(
                models.JourneyStep.hospital_id == self.hospital_id,
                models.JourneyStep.status.in_(ACTIVE_STEP_STATUSES),
            )
        )
        active = list(active_result.scalars().all())

        start_of_day = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        completed_result = await self.db.execute(
            select(models.JourneyStep).where(
                models.JourneyStep.hospital_id == self.hospital_id,
                models.JourneyStep.status == schemas.StepStatus.completed.value,
                models.JourneyStep.completed_at >= start_of_day,
            )
        )
        completed = list(completed_result.scalars().all())

        waiting = sum(1 for s in active if s.status == schemas.StepStatus.waiting.value)
        called = sum(1 for s in active if s.status == schemas.StepStatus.called.value)
        in_progress = sum(
            1 for s in active if s.status == schemas.StepStatus.in_progress.value
        )

        by_priority: dict[str, int] = {}
        by_service_point: dict[str, int] = {}
        for step in active:
            by_priority[step.priority] = by_priority.get(step.priority, 0) + 1
            by_service_point[step.service_point] = (
                by_service_point.get(step.service_point, 0) + 1
            )

        waits = [
            calculate_wait_minutes(step.created_at, step.completed_at)
            for step in completed
            if step.completed_at is not None
        ]
        active_waits = [calculate_wait_minutes(step.created_at) for step in active]

        return schemas.FlowStatsResponse(
            waiting=waiting,
            called=called,
            in_progress=in_progress,
            active_total=len(active),
            completed_today=len(completed),
            by_priority=by_priority,
            by_service_point=by_service_point,
            average_wait_minutes=round(sum(waits) / len(waits), 1) if waits else 0.0,
            longest_wait_minutes=max(active_waits) if active_waits else 0,
        )

    async def get_destinations(self) -> schemas.DestinationsResponse:
        departments: list[Department] = []
        staff: list[Staff] = []

        # Department/staff tables come from the ORM-managed hospital schema,
        # which is not present in every legacy database. Degrade gracefully so
        # that the queue and service-point routing still work.
        try:
            async with self.db.begin_nested():
                department_result = await self.db.execute(
                    select(Department)
                    .where(
                        Department.hospital_id == self.hospital_id,
                        Department.is_active == True,  # noqa: E712
                    )
                    .order_by(Department.name)
                )
                departments = list(department_result.scalars().all())
        except Exception as exc:  # pragma: no cover - depends on deployment schema
            logger.warning("Department directory unavailable: %s", exc)

        department_names = {d.id: d.name for d in departments}

        try:
            async with self.db.begin_nested():
                staff_result = await self.db.execute(
                    select(Staff)
                    .where(
                        Staff.hospital_id == self.hospital_id,
                        Staff.is_active == True,  # noqa: E712
                        Staff.role.in_(DESTINATION_STAFF_ROLES),
                    )
                    .order_by(Staff.last_name, Staff.first_name)
                )
                staff = list(staff_result.scalars().all())
        except Exception as exc:  # pragma: no cover - depends on deployment schema
            logger.warning("Staff directory unavailable: %s", exc)

        return schemas.DestinationsResponse(
            departments=[
                schemas.DestinationDepartment(
                    id=d.id, name=d.name, code=d.code, location=d.location
                )
                for d in departments
            ],
            staff=[
                schemas.DestinationStaff(
                    id=s.id,
                    user_id=s.user_id,
                    name=f"{s.first_name} {s.last_name}".strip(),
                    role=_enum_value(s.role),
                    speciality=s.speciality,
                    department_id=s.department_id,
                    department_name=department_names.get(s.department_id),
                )
                for s in staff
            ],
            service_points=SERVICE_POINTS,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _journey_with_step(
        self, journey_id: uuid.UUID, step_id: uuid.UUID
    ) -> models.PatientJourney:
        journey = await self.get_journey(journey_id)
        if journey is None:
            raise LookupError("Journey not found")
        self._find_step(journey, step_id)
        return journey

    @staticmethod
    def _find_step(
        journey: models.PatientJourney, step_id: uuid.UUID
    ) -> models.JourneyStep:
        for step in journey.steps:
            if step.id == step_id:
                return step
        raise LookupError("Journey step not found")

    @staticmethod
    def _find_current_step(
        journey: models.PatientJourney,
    ) -> Optional[models.JourneyStep]:
        if journey.current_step_id is not None:
            for step in journey.steps:
                if step.id == journey.current_step_id:
                    return step
        active = [s for s in journey.steps if s.status in ACTIVE_STEP_STATUSES]
        if active:
            return active[-1]
        return journey.steps[-1] if journey.steps else None

    @staticmethod
    def _transition_step(step: models.JourneyStep, target: str) -> None:
        if step.status == target:
            return
        if not can_transition_step(step.status, target):
            raise ValueError(
                f"Cannot move journey step from '{step.status}' to '{target}'"
            )
        step.status = target

    def _make_current(
        self, journey: models.PatientJourney, step: models.JourneyStep
    ) -> None:
        journey.current_step_id = step.id
        journey.current_step_type = step.step_type
        journey.current_service_point = step.service_point
        journey.current_department_id = step.department_id
        journey.current_department_name = step.department_name
        journey.current_provider_id = step.provider_id
        journey.current_provider_name = step.provider_name

    def _finish_step(
        self,
        step: models.JourneyStep,
        outcome: str,
        notes: Optional[str] = None,
        status: str = schemas.StepStatus.completed.value,
    ) -> None:
        self._transition_step(step, status)
        step.outcome = outcome
        step.completed_at = datetime.utcnow()
        if notes:
            step.notes = notes
        step.updated_by = self.user_id

    @staticmethod
    def _clear_current_if_matches(
        journey: models.PatientJourney, step: models.JourneyStep
    ) -> None:
        if journey.current_step_id == step.id:
            journey.current_step_id = None
            journey.current_step_type = None
            journey.current_service_point = None
            journey.current_department_id = None
            journey.current_department_name = None
            journey.current_provider_id = None
            journey.current_provider_name = None
