import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from src.backend.services.emr.schemas import ClinicalNoteCreate
from src.backend.services.emr.services import ClinicalNoteService


class ClinicalNoteSaveTests(unittest.IsolatedAsyncioTestCase):
    async def test_soap_note_uses_authenticated_author_and_database_timestamp_format(self):
        patient_id = uuid.uuid4()
        hospital_id = uuid.uuid4()
        db = SimpleNamespace(scalar=AsyncMock(return_value=patient_id), add=Mock(), flush=AsyncMock())
        service = ClinicalNoteService(db, hospital_id, "staff-id", "doctor")
        data = ClinicalNoteCreate(
            patient_id=patient_id,
            note_type="SOAP",
            subjective="Test note",
            authored_by="client-supplied author",
            authored_datetime=datetime.now(timezone.utc),
        )

        note = await service.create_note(data)

        self.assertEqual(note.hospital_id, hospital_id)
        self.assertEqual(note.created_by, "staff-id")
        self.assertEqual(note.authored_by, "doctor")
        self.assertIsNone(note.authored_datetime.tzinfo)
        db.flush.assert_awaited_once()

    async def test_create_rejects_patient_outside_facility(self):
        db = SimpleNamespace(scalar=AsyncMock(return_value=None), add=Mock())
        service = ClinicalNoteService(db, uuid.uuid4(), "staff-id")
        with self.assertRaisesRegex(LookupError, "Patient not found at this facility"):
            await service.create_note(ClinicalNoteCreate(patient_id=uuid.uuid4(), note_type="SOAP"))
        db.add.assert_not_called()
