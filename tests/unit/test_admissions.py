"""Admission invariants; runnable with unittest in the EMR dependency image."""
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from src.backend.services.hospital_management.models import BedStatus
from src.backend.services.hospital_management.schemas import AdmissionCreate
from src.backend.services.hospital_management.services import BedManagementService


class AdmissionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_admission_links_encounter_and_updates_occupancy(self):
        patient = SimpleNamespace(id=uuid.uuid4(), gender=SimpleNamespace(value="female"))
        bed = SimpleNamespace(status=BedStatus.available, ward_id=uuid.uuid4())
        ward = SimpleNamespace(current_occupancy=0, capacity=2, gender_restriction=None, name="General")
        db = SimpleNamespace(scalar=AsyncMock(side_effect=[patient, None, bed, ward]), flush=AsyncMock(), add=Mock())
        service = BedManagementService(db, uuid.uuid4(), "doctor")
        result = await service.admit_patient(uuid.uuid4(), AdmissionCreate(patient_id=patient.id, reason="Observation"))
        self.assertIs(result, bed)
        self.assertEqual(bed.current_patient_id, patient.id)
        self.assertEqual(bed.status, BedStatus.occupied)
        self.assertEqual(ward.current_occupancy, 1)
        self.assertEqual(db.add.call_args.args[0].chief_complaint, "Observation")

    async def test_unknown_patient_never_creates_encounter(self):
        db = SimpleNamespace(scalar=AsyncMock(return_value=None), flush=AsyncMock())
        service = BedManagementService(db, uuid.uuid4(), "doctor")
        with self.assertRaises(LookupError):
            await service.admit_patient(uuid.uuid4(), AdmissionCreate(patient_id=uuid.uuid4(), reason="Observation"))
        db.flush.assert_not_awaited()

    async def test_existing_admission_rejected_before_bed_change(self):
        db = SimpleNamespace(scalar=AsyncMock(side_effect=[SimpleNamespace(id=uuid.uuid4()), uuid.uuid4()]), flush=AsyncMock())
        service = BedManagementService(db, uuid.uuid4(), "doctor")
        with self.assertRaisesRegex(ValueError, "active inpatient"):
            await service.admit_patient(uuid.uuid4(), AdmissionCreate(patient_id=uuid.uuid4(), reason="Observation"))
        db.flush.assert_not_awaited()

    async def test_occupied_bed_never_creates_encounter(self):
        bed = SimpleNamespace(status=BedStatus.occupied)
        db = SimpleNamespace(scalar=AsyncMock(side_effect=[SimpleNamespace(id=uuid.uuid4()), None, bed]), flush=AsyncMock())
        service = BedManagementService(db, uuid.uuid4(), "doctor")
        with self.assertRaisesRegex(ValueError, "no longer available"):
            await service.admit_patient(uuid.uuid4(), AdmissionCreate(patient_id=uuid.uuid4(), reason="Observation"))
        db.flush.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
