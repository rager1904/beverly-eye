"""PostgreSQL regression test; opt in with PATIENT_FLOW_DB_TESTS=1.

Uses a registered patient's ID without changing that record. All journey/step
writes are rolled back, including on failure. Run in the EMR dependency image.
"""
import os
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from src.backend.database import async_session_factory, engine
from src.backend.services.emr.dependencies import EMRSession, get_emr_session
from src.backend.services.emr.main import app as emr_app  # noqa: F401
from src.backend.services.emr.models import Patient
from src.backend.services.patient_flow.models import JourneyStep, PatientJourney
from src.backend.services.patient_flow.routers.journeys import require_flow_write, router


@unittest.skipUnless(os.getenv("PATIENT_FLOW_DB_TESTS") == "1", "Requires opt-in PostgreSQL access")
class PatientFlowDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        await engine.dispose()

    async def test_create_read_and_route_without_implicit_database_io(self):
        async with async_session_factory() as db:
            row = (await db.execute(select(Patient.id, Patient.hospital_id).where(
                Patient.hospital_id.is_not(None),
            ).limit(1))).first()
            if row is None:
                self.skipTest("Requires one registered patient")

            patient_id, hospital_id = row
            session = object.__new__(EMRSession)
            session.db = db
            session.hospital_id = hospital_id
            session.user_id = "patient-flow-regression-test"
            session.user_name = "Regression test"

            # Exercise the real router, response serialization and database;
            # authentication is replaced only inside this isolated test app.
            test_app = FastAPI()
            test_app.include_router(router, prefix="/api/v1/patient-flow")
            test_app.dependency_overrides[get_emr_session] = lambda: session
            test_app.dependency_overrides[require_flow_write] = lambda: None
            journey_id = None
            try:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=test_app), base_url="http://test",
                ) as client:
                    created = await client.post("/api/v1/patient-flow/journeys", json={
                        "patient_id": str(patient_id), "arrival_notes": "Rollback-only regression test",
                    })
                    self.assertEqual(created.status_code, 201, created.text)
                    journey = created.json()
                    journey_id = journey["id"]
                    self.assertEqual(len(journey["steps"]), 1)
                    self.assertEqual(journey["current_step_id"], journey["steps"][0]["id"])
                    self.assertEqual(journey["patient_id"], str(patient_id))

                    fetched = await client.get(f"/api/v1/patient-flow/journeys/{journey_id}")
                    self.assertEqual(fetched.status_code, 200, fetched.text)
                    self.assertEqual(len(fetched.json()["steps"]), 1)

                    routed = await client.post(f"/api/v1/patient-flow/journeys/{journey_id}/route", json={
                        "step_type": "triage", "service_point": "triage",
                    })
                    self.assertEqual(routed.status_code, 200, routed.text)
                    self.assertEqual(len(routed.json()["steps"]), 2)
                    self.assertEqual(routed.json()["steps"][0]["status"], "completed")
                    self.assertEqual(routed.json()["current_service_point"], "triage")
                    step_id = routed.json()["current_step_id"]
                    for action, expected in (("call", "called"), ("start", "in_progress"), ("complete", "completed")):
                        response = await client.post(
                            f"/api/v1/patient-flow/journeys/{journey_id}/steps/{step_id}/{action}",
                            json={} if action == "complete" else None,
                        )
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.json()["steps"][-1]["status"], expected)
                    closed = await client.post(f"/api/v1/patient-flow/journeys/{journey_id}/close", json={})
                    self.assertEqual(closed.status_code, 200, closed.text)
                    self.assertEqual(closed.json()["status"], "completed")
            finally:
                await db.rollback()

            if journey_id:
                import uuid
                identity = uuid.UUID(journey_id)
                self.assertIsNone(await db.scalar(select(PatientJourney.id).where(PatientJourney.id == identity)))
                self.assertIsNone(await db.scalar(select(JourneyStep.id).where(JourneyStep.journey_id == identity)))


if __name__ == "__main__":
    unittest.main()
