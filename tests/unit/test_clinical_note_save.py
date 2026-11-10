import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from src.backend.services.emr import models
from src.backend.services.emr.schemas import ClinicalNoteCreate, ClinicalNoteUpdate
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

    async def test_create_links_note_to_patient_and_matching_encounter(self):
        patient_id = uuid.uuid4()
        encounter_id = uuid.uuid4()
        hospital_id = uuid.uuid4()
        db = SimpleNamespace(
            scalar=AsyncMock(side_effect=[patient_id, encounter_id]),
            add=Mock(),
            flush=AsyncMock(),
        )
        service = ClinicalNoteService(db, hospital_id, "staff-id")

        note = await service.create_note(
            ClinicalNoteCreate(
                patient_id=patient_id,
                encounter_id=encounter_id,
                note_type="SOAP",
                assessment="Assessment for this patient",
            )
        )

        self.assertEqual(note.patient_id, patient_id)
        self.assertEqual(note.encounter_id, encounter_id)
        self.assertEqual(note.hospital_id, hospital_id)
        db.add.assert_called_once_with(note)

    async def test_create_rejects_encounter_not_belonging_to_patient_or_hospital(self):
        patient_id = uuid.uuid4()
        encounter_id = uuid.uuid4()
        db = SimpleNamespace(
            scalar=AsyncMock(side_effect=[patient_id, None]),
            add=Mock(),
        )
        service = ClinicalNoteService(db, uuid.uuid4(), "staff-id")

        with self.assertRaisesRegex(LookupError, "Encounter not found for this patient"):
            await service.create_note(
                ClinicalNoteCreate(
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    note_type="SOAP",
                )
            )

        db.add.assert_not_called()

    def test_update_schema_rejects_patient_or_encounter_reassignment(self):
        note_id = uuid.uuid4()

        for association_field in ("patient_id", "encounter_id"):
            with self.subTest(field=association_field):
                with self.assertRaisesRegex(ValueError, association_field):
                    ClinicalNoteUpdate(**{association_field: note_id})

    async def test_update_preserves_existing_patient_and_encounter_associations(self):
        patient_id = uuid.uuid4()
        encounter_id = uuid.uuid4()
        note = SimpleNamespace(
            status=models.NoteStatus.draft,
            patient_id=patient_id,
            encounter_id=encounter_id,
            updated_by=None,
            assessment="Original assessment",
        )
        db = SimpleNamespace(flush=AsyncMock(), refresh=AsyncMock())
        service = ClinicalNoteService(db, uuid.uuid4(), "staff-id")
        service.get_note = AsyncMock(return_value=note)

        updated = await service.update_note(uuid.uuid4(), ClinicalNoteUpdate(assessment="Updated assessment"))

        self.assertEqual(updated.patient_id, patient_id)
        self.assertEqual(updated.encounter_id, encounter_id)
        self.assertEqual(updated.assessment, "Updated assessment")
