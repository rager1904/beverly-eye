"""Patient flow tests: workflow state machine, routing and RBAC.

Runs with the standard library test runner / pytest without a database.
"""

import re
import unittest
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from src.backend.security.rbac.middleware import RBACMiddleware
from src.backend.security.rbac.permissions import PermissionSet
from src.backend.services.patient_flow import schemas, services


class PatientFlowPermissionTests(unittest.TestCase):
    def test_doctor_can_route_and_complete_steps(self):
        permissions = PermissionSet.from_roles(["doctor"])
        assert permissions.has_permission("patient_flow:read")
        assert permissions.has_permission("patient_flow:write")

    def test_records_officer_can_register_and_route(self):
        permissions = PermissionSet.from_roles(["records_officer"])
        assert permissions.has_permission("patient_flow:read")
        assert permissions.has_permission("patient_flow:write")
        assert permissions.has_permission("patient:read")

    def test_medical_records_alias_has_flow_access(self):
        permissions = PermissionSet.from_roles(["medical_records"])
        assert permissions.has_permission("patient_flow:write")

    def test_lab_technician_can_receive_patients(self):
        permissions = PermissionSet.from_roles(["lab_technician"])
        assert permissions.has_permission("patient_flow:write")
        assert permissions.has_permission("lab:result")

    def test_patient_cannot_manage_the_queue(self):
        permissions = PermissionSet.from_roles(["patient"])
        assert not permissions.has_permission("patient_flow:read")
        assert not permissions.has_permission("patient_flow:write")

    def test_read_and_write_are_method_aware(self):
        mapping = {
            "GET": "patient_flow:read",
            "HEAD": "patient_flow:read",
            "default": "patient_flow:write",
        }
        assert RBACMiddleware._required_permission(mapping, "GET") == "patient_flow:read"
        assert RBACMiddleware._required_permission(mapping, "POST") == "patient_flow:write"
        assert RBACMiddleware._required_permission(mapping, "PATCH") == "patient_flow:write"


class PatientFlowHelperTests(unittest.TestCase):
    def test_general_eye_and_dental_destinations_are_available(self):
        destinations = {point.code: point for point in services.SERVICE_POINTS}
        assert destinations["general"].step_type == schemas.StepType.consultation
        assert destinations["eye"].step_type == schemas.StepType.consultation
        assert destinations["dental"].step_type == schemas.StepType.consultation
        assert {"general", "eye", "dental"}.issubset(destinations)
        assert not {"ophthalmology", "optometry", "oral_surgery"}.intersection(destinations)

    def test_step_state_machine_allows_normal_progression(self):
        assert services.can_transition_step("waiting", "called")
        assert services.can_transition_step("called", "in_progress")
        assert services.can_transition_step("in_progress", "completed")

    def test_step_state_machine_rejects_reopening_closed_steps(self):
        assert not services.can_transition_step("completed", "in_progress")
        assert not services.can_transition_step("skipped", "waiting")
        assert not services.can_transition_step("cancelled", "called")

    def test_journey_number_is_readable_and_unique(self):
        first = services.build_journey_number(datetime(2026, 10, 29))
        second = services.build_journey_number(datetime(2026, 10, 29))
        assert re.fullmatch(r"PF-20261029-[A-F0-9]{6}", first)
        assert first != second

    def test_wait_minutes_are_never_negative(self):
        now = datetime(2026, 10, 29, 10, 0)
        assert services.calculate_wait_minutes(now - timedelta(minutes=25), now) == 25
        assert services.calculate_wait_minutes(now, now - timedelta(minutes=5)) == 0

    def test_priority_order_puts_emergencies_first(self):
        priorities = ["routine", "urgent", "emergency"]
        ordered = sorted(priorities, key=services.priority_sort_key)
        assert ordered == ["emergency", "urgent", "routine"]


class PatientFlowSchemaTests(unittest.TestCase):
    def test_journey_defaults_to_registration_counter(self):
        data = schemas.JourneyCreate(patient_id=uuid.uuid4())
        assert data.step_type == schemas.StepType.registration
        assert data.service_point == "registration"
        assert data.priority == schemas.JourneyPriority.routine

    def test_route_requires_a_destination(self):
        with pytest.raises(ValidationError):
            schemas.RouteRequest(step_type=schemas.StepType.laboratory, service_point="")

    def test_route_defaults_outcome_to_referred(self):
        data = schemas.RouteRequest(
            step_type=schemas.StepType.consultation,
            service_point="consultation",
            provider_name="Dr Mwamba",
        )
        assert data.outcome == schemas.StepOutcome.referred

    def test_journey_captures_billing_and_visit_details(self):
        data = schemas.JourneyCreate(
            patient_id=uuid.uuid4(),
            payment_scheme=schemas.PaymentScheme.nhima,
            visit_type=schemas.VisitType.review,
            payment_status=schemas.VisitPaymentStatus.paid,
            scheme_number="NHIMA-100001",
        )
        assert data.payment_scheme == schemas.PaymentScheme.nhima
        assert data.visit_type == schemas.VisitType.review
        assert data.payment_status == schemas.VisitPaymentStatus.paid
        assert data.scheme_number == "NHIMA-100001"

    def test_journey_defaults_billing_to_cash_unpaid_new_visit(self):
        data = schemas.JourneyCreate(patient_id=uuid.uuid4())
        assert data.payment_scheme == schemas.PaymentScheme.cash
        assert data.visit_type == schemas.VisitType.new
        assert data.payment_status == schemas.VisitPaymentStatus.unpaid

    def test_unknown_payment_scheme_is_rejected(self):
        with pytest.raises(ValidationError):
            schemas.JourneyCreate(patient_id=uuid.uuid4(), payment_scheme="not-a-scheme")


class PatientJourneyServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_journey_opens_first_queue_step(self):
        db = SimpleNamespace(add=Mock(), flush=AsyncMock())
        patient_id = uuid.uuid4()
        hospital_id = uuid.uuid4()
        service = services.JourneyService(db, hospital_id, "clerk")
        service._get_patient_summary = AsyncMock(
            return_value=schemas.FlowPatientSummary(
                id=patient_id, first_name="Grace", last_name="Banda"
            )
        )

        journey = await service.create_journey(
            schemas.JourneyCreate(
                patient_id=patient_id,
                priority=schemas.JourneyPriority.urgent,
                step_type=schemas.StepType.consultation,
                service_point="consultation",
                department_name="Outpatient",
                provider_name="Dr Mwamba",
                chief_complaint="Fever",
            )
        )

        self.assertEqual(journey.status, schemas.JourneyStatus.waiting.value)
        self.assertEqual(journey.priority, "urgent")
        self.assertEqual(journey.payment_scheme, "cash")
        self.assertEqual(journey.visit_type, "new")
        self.assertEqual(journey.payment_status, "unpaid")
        self.assertEqual(len(journey.steps), 1)
        step = journey.steps[0]
        self.assertEqual(step.step_number, 1)
        self.assertEqual(step.service_point, "consultation")
        self.assertEqual(step.status, schemas.StepStatus.waiting.value)
        self.assertEqual(journey.current_step_id, step.id)
        self.assertEqual(db.add.call_count, 2)

    async def test_create_journey_persists_registration_billing_fields(self):
        db = SimpleNamespace(add=Mock(), flush=AsyncMock())
        patient_id = uuid.uuid4()
        service = services.JourneyService(db, uuid.uuid4(), "clerk")
        service._get_patient_summary = AsyncMock(
            return_value=schemas.FlowPatientSummary(
                id=patient_id, first_name="Chanda", last_name="Mbewe"
            )
        )

        journey = await service.create_journey(
            schemas.JourneyCreate(
                patient_id=patient_id,
                payment_scheme=schemas.PaymentScheme.prudential,
                visit_type=schemas.VisitType.review,
                payment_status=schemas.VisitPaymentStatus.paid,
                scheme_number="PRU-7788",
            )
        )

        self.assertEqual(journey.payment_scheme, "prudential")
        self.assertEqual(journey.visit_type, "review")
        self.assertEqual(journey.payment_status, "paid")
        self.assertEqual(journey.scheme_number, "PRU-7788")

    async def test_route_completes_current_step_and_opens_next(self):
        db = SimpleNamespace(add=Mock(), flush=AsyncMock())
        hospital_id = uuid.uuid4()
        journey = SimpleNamespace(
            id=uuid.uuid4(),
            hospital_id=hospital_id,
            patient_id=uuid.uuid4(),
            journey_number="PF-20261029-ABC123",
            status=schemas.JourneyStatus.waiting.value,
            priority="urgent",
            current_step_id=None,
            current_step_type=None,
            current_service_point=None,
            current_department_id=None,
            current_department_name=None,
            current_provider_id=None,
            current_provider_name=None,
            started_at=None,
            updated_by=None,
            steps=[],
        )
        current = SimpleNamespace(
            id=uuid.uuid4(),
            step_number=1,
            step_type="consultation",
            service_point="consultation",
            status=schemas.StepStatus.in_progress.value,
            outcome=None,
            notes=None,
            completed_at=None,
            referred_to_step_type=None,
            referred_to_service_point=None,
            referred_to_department_id=None,
            referred_to_provider_id=None,
            updated_by=None,
        )
        journey.steps.append(current)
        journey.current_step_id = current.id

        service = services.JourneyService(db, hospital_id, "doctor")
        service.get_journey = AsyncMock(return_value=journey)

        result = await service.route_patient(
            journey.id,
            schemas.RouteRequest(
                step_type=schemas.StepType.laboratory,
                service_point="laboratory",
                department_name="Laboratory",
                reason="Full blood count",
            ),
        )

        self.assertEqual(current.status, schemas.StepStatus.completed.value)
        self.assertEqual(current.outcome, schemas.StepOutcome.referred.value)
        self.assertEqual(current.referred_to_service_point, "laboratory")
        self.assertIsNotNone(current.completed_at)

        self.assertEqual(len(result.steps), 2)
        new_step = result.steps[1]
        self.assertEqual(new_step.step_number, 2)
        self.assertEqual(new_step.service_point, "laboratory")
        self.assertEqual(new_step.status, schemas.StepStatus.waiting.value)
        self.assertEqual(result.current_step_id, new_step.id)
        self.assertEqual(result.current_service_point, "laboratory")
        self.assertEqual(result.status, schemas.JourneyStatus.waiting.value)

    async def test_closing_journey_completes_active_step(self):
        db = SimpleNamespace(add=Mock(), flush=AsyncMock())
        hospital_id = uuid.uuid4()
        journey = SimpleNamespace(
            id=uuid.uuid4(),
            hospital_id=hospital_id,
            patient_id=uuid.uuid4(),
            journey_number="PF-20261029-ABC123",
            status=schemas.JourneyStatus.in_progress.value,
            priority="routine",
            current_step_id=None,
            current_step_type="consultation",
            current_service_point="consultation",
            current_department_id=None,
            current_department_name=None,
            current_provider_id=None,
            current_provider_name=None,
            started_at=datetime.utcnow(),
            completed_at=None,
            closed_reason=None,
            updated_by=None,
            steps=[],
        )
        current = SimpleNamespace(
            id=uuid.uuid4(),
            step_number=1,
            step_type="consultation",
            service_point="consultation",
            status=schemas.StepStatus.in_progress.value,
            outcome=None,
            notes=None,
            completed_at=None,
            updated_by=None,
        )
        journey.steps.append(current)
        journey.current_step_id = current.id

        service = services.JourneyService(db, hospital_id, "doctor")
        service.get_journey = AsyncMock(return_value=journey)

        result = await service.close_journey(
            journey.id, schemas.CloseJourneyRequest(reason="Treatment complete")
        )

        self.assertEqual(current.status, schemas.StepStatus.completed.value)
        self.assertEqual(current.outcome, schemas.StepOutcome.discharged.value)
        self.assertEqual(result.status, schemas.JourneyStatus.completed.value)
        self.assertIsNone(result.current_step_id)
        self.assertEqual(result.closed_reason, "Treatment complete")


if __name__ == "__main__":
    unittest.main()

def test_latest_handoff_visibility_is_limited_to_its_participants():
    from sqlalchemy import create_engine, select

    from src.backend.services.patient_flow import models

    hospital_id = uuid.uuid4()
    journey_id = uuid.uuid4()
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE patient_journeys (id TEXT PRIMARY KEY)")
        conn.exec_driver_sql(
            "CREATE TABLE journey_steps (id TEXT, journey_id TEXT, hospital_id TEXT, "
            "step_number INTEGER, created_by TEXT, provider_id TEXT)"
        )
        conn.exec_driver_sql("INSERT INTO patient_journeys VALUES (?)", (journey_id.hex,))
        conn.exec_driver_sql(
            "INSERT INTO journey_steps VALUES (?, ?, ?, ?, ?, ?)",
            [
                (uuid.uuid4().hex, journey_id.hex, hospital_id.hex, 1, "reception", "nurse"),
                (uuid.uuid4().hex, journey_id.hex, hospital_id.hex, 2, "nurse", "doctor"),
            ],
        )

        for identity, visible in (
            ("nurse", True), ("doctor", True), ("reception", False), ("other", False), (None, False)
        ):
            service = services.JourneyService(None, hospital_id, identity)
            query = select(models.PatientJourney.id).where(service._latest_handoff_participant())
            assert (conn.scalar(query) == journey_id) == visible
    engine.dispose()
