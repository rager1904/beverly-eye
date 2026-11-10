import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.config import settings

from . import models, schemas

logger = logging.getLogger(__name__)


class PatientService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None,
                 user_name: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id
        self.user_name = user_name

    async def _lookup_nrc(self, nrc_number: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.smartcare_api_url}/nrc/{nrc_number}",
                    headers={"Authorization": f"Bearer {settings.smartcare_api_key}"},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning("SmartCare NRC lookup failed (%s)", type(e).__name__)
        return None

    async def _check_smartcare_duplicate(self, smartcare_id: str) -> bool:
        result = await self.db.execute(
            select(models.Patient).where(
                models.Patient.smartcare_id == smartcare_id,
                models.Patient.hospital_id == self.hospital_id,
                models.Patient.is_active == True,
            )
        )
        return result.scalar_one_or_none() is not None

    async def register_patient(self, data: schemas.PatientCreate) -> models.Patient:
        if data.nrc_number:
            nrc_data = await self._lookup_nrc(data.nrc_number)
            if nrc_data:
                data.first_name = nrc_data.get("first_name", data.first_name)
                data.last_name = nrc_data.get("surname", data.last_name)
                data.date_of_birth = datetime.strptime(
                    nrc_data["date_of_birth"], "%Y-%m-%d"
                ).date()
                data.gender = models.Gender(nrc_data.get("gender", "male").lower())

        if data.smartcare_id:
            dup = await self._check_smartcare_duplicate(data.smartcare_id)
            if dup:
                raise ValueError(f"Patient with Smartcare ID {data.smartcare_id} already exists")

        patient = models.Patient(
            hospital_id=self.hospital_id,
            created_by=self.user_id,
            **data.model_dump(),
        )
        self.db.add(patient)
        await self.db.flush()

        logger.info(
            "Patient registered",
            extra={
                "patient_id": str(patient.id),
                "hospital_id": str(self.hospital_id),
            },
        )
        return patient

    async def get_patient(self, patient_id: uuid.UUID) -> Optional[models.Patient]:
        result = await self.db.execute(
            select(models.Patient).where(
                models.Patient.id == patient_id,
                models.Patient.hospital_id == self.hospital_id,
                models.Patient.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def search_patients(
        self,
        query: Optional[str] = None,
        nrc_number: Optional[str] = None,
        phone: Optional[str] = None,
        province: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.Patient], int]:
        stmt = select(models.Patient).where(
            models.Patient.hospital_id == self.hospital_id,
            models.Patient.is_active == True,
        )
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    models.Patient.first_name.ilike(pattern),
                    models.Patient.last_name.ilike(pattern),
                    models.Patient.nrc_number.ilike(pattern),
                    models.Patient.phone.ilike(pattern),
                )
            )
        if nrc_number:
            stmt = stmt.where(models.Patient.nrc_number == nrc_number)
        if phone:
            stmt = stmt.where(models.Patient.phone == phone)
        if province:
            stmt = stmt.where(models.Patient.province == province)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(models.Patient.last_name, models.Patient.first_name)
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_patient(self, patient_id: uuid.UUID, data: schemas.PatientUpdate) -> Optional[models.Patient]:
        patient = await self.get_patient(patient_id)
        if not patient:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return patient
        update_data["updated_by"] = self.user_id
        await self.db.execute(
            update(models.Patient)
            .where(models.Patient.id == patient_id)
            .values(**update_data)
        )
        await self.db.flush()
        await self.db.refresh(patient)
        return await self.get_patient(patient_id)

    async def soft_delete_patient(self, patient_id: uuid.UUID) -> bool:
        patient = await self.get_patient(patient_id)
        if not patient:
            return False
        await self.db.execute(
            update(models.Patient)
            .where(models.Patient.id == patient_id)
            .values(is_active=False, deleted_at=datetime.utcnow(), deleted_by=self.user_id)
        )
        await self.db.flush()
        logger.warning("Patient soft-deleted", extra={"patient_id": str(patient_id)})
        return True


class EncounterService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None,
                 user_name: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id
        self.user_name = user_name

    async def create_encounter(self, data: schemas.EncounterCreate) -> models.Encounter:
        encounter = models.Encounter(
            hospital_id=self.hospital_id,
            status=models.EncounterStatus.in_progress,
            created_by=self.user_id,
            **data.model_dump(),
        )
        self.db.add(encounter)
        await self.db.flush()
        logger.info("Encounter created", extra={"encounter_id": str(encounter.id), "patient_id": str(data.patient_id)})
        return encounter

    async def get_encounter(self, encounter_id: uuid.UUID) -> Optional[models.Encounter]:
        result = await self.db.execute(
            select(models.Encounter)
            .where(
                models.Encounter.id == encounter_id,
                models.Encounter.hospital_id == self.hospital_id,
            )
            .options(selectinload(models.Encounter.diagnoses))
        )
        return result.scalar_one_or_none()

    async def list_encounters(
        self,
        patient_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        encounter_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.Encounter], int]:
        stmt = select(models.Encounter).where(
            models.Encounter.hospital_id == self.hospital_id
        )
        if patient_id:
            stmt = stmt.where(models.Encounter.patient_id == patient_id)
        if status:
            stmt = stmt.where(models.Encounter.status == status)
        if encounter_type:
            stmt = stmt.where(models.Encounter.encounter_type == encounter_type)
        if from_date:
            stmt = stmt.where(models.Encounter.encounter_datetime >= from_date)
        if to_date:
            stmt = stmt.where(models.Encounter.encounter_datetime <= to_date)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(models.Encounter.encounter_datetime.desc())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_encounter(self, encounter_id: uuid.UUID, data: schemas.EncounterUpdate) -> Optional[models.Encounter]:
        encounter = await self.get_encounter(encounter_id)
        if not encounter:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return encounter
        update_data["updated_by"] = self.user_id
        await self.db.execute(
            update(models.Encounter)
            .where(models.Encounter.id == encounter_id)
            .values(**update_data)
        )
        await self.db.flush()
        return await self.get_encounter(encounter_id)

    async def discharge(self, encounter_id: uuid.UUID) -> Optional[models.Encounter]:
        return await self.update_encounter(
            encounter_id,
            schemas.EncounterUpdate(status=models.EncounterStatus.discharged),
        )


class DiagnosisService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def add_diagnosis(self, data: schemas.DiagnosisCreate) -> models.Diagnosis:
        diagnosis = models.Diagnosis(
            hospital_id=self.hospital_id,
            **data.model_dump(),
        )
        self.db.add(diagnosis)
        await self.db.flush()
        return diagnosis

    async def get_encounter_diagnoses(self, encounter_id: uuid.UUID) -> list[models.Diagnosis]:
        result = await self.db.execute(
            select(models.Diagnosis).where(
                models.Diagnosis.encounter_id == encounter_id,
                models.Diagnosis.hospital_id == self.hospital_id,
            ).order_by(models.Diagnosis.sequence)
        )
        return list(result.scalars().all())

    async def update_diagnosis(self, diagnosis_id: uuid.UUID, data: schemas.DiagnosisUpdate) -> Optional[models.Diagnosis]:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            result = await self.db.execute(
                select(models.Diagnosis).where(models.Diagnosis.id == diagnosis_id)
            )
            return result.scalar_one_or_none()
        await self.db.execute(
            update(models.Diagnosis)
            .where(models.Diagnosis.id == diagnosis_id)
            .values(**update_data)
        )
        await self.db.flush()
        result = await self.db.execute(
            select(models.Diagnosis).where(models.Diagnosis.id == diagnosis_id)
        )
        return result.scalar_one_or_none()

    async def search_icd10(self, query: str) -> list[dict]:
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://icd10api.com/search",
                    params={"query": query, "format": "json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        results.append({
                            "code": item.get("code", ""),
                            "description": item.get("description", ""),
                        })
        except Exception as e:
            logger.warning(f"ICD-10 search failed: {e}")
            results = self._local_icd10_search(query)
        return results

    def _local_icd10_search(self, query: str) -> list[dict]:
        q = query.lower()
        local_db = {
            "A00": "Cholera",
            "A01": "Typhoid fever",
            "A02": "Salmonella infection",
            "A09": "Infectious gastroenteritis",
            "B20": "HIV disease",
            "E10": "Type 1 diabetes mellitus",
            "E11": "Type 2 diabetes mellitus",
            "I10": "Essential hypertension",
            "I50": "Heart failure",
            "J15": "Bacterial pneumonia",
            "J45": "Asthma",
            "K21": "GERD",
            "K29": "Gastritis",
            "M54": "Back pain",
            "N39": "UTI",
            "O80": "Single spontaneous delivery",
            "R50": "Fever",
            "R51": "Headache",
            "R53": "Malai se and fatigue",
        }
        return [
            {"code": k, "description": v}
            for k, v in local_db.items()
            if q in v.lower() or q in k.lower()
        ]


class MedicationService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def prescribe(self, data: schemas.MedicationCreate) -> models.Medication:
        medication = models.Medication(
            hospital_id=self.hospital_id,
            status=models.MedicationStatus.prescribed,
            **data.model_dump(),
        )
        self.db.add(medication)
        await self.db.flush()
        return medication

    async def get_patient_medications(self, patient_id: uuid.UUID) -> list[models.Medication]:
        result = await self.db.execute(
            select(models.Medication)
            .where(
                models.Medication.patient_id == patient_id,
                models.Medication.hospital_id == self.hospital_id,
            )
            .order_by(models.Medication.created_at.desc())
        )
        return list(result.scalars().all())

    async def administer(self, medication_id: uuid.UUID, admin_by: str) -> Optional[models.Medication]:
        await self.db.execute(
            update(models.Medication)
            .where(models.Medication.id == medication_id)
            .values(
                status=models.MedicationStatus.administered,
                administered_by=admin_by,
                administered_at=datetime.utcnow(),
            )
        )
        await self.db.flush()
        result = await self.db.execute(
            select(models.Medication).where(models.Medication.id == medication_id)
        )
        return result.scalar_one_or_none()


class AllergyService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def add_allergy(self, data: schemas.AllergyCreate) -> models.Allergy:
        allergy = models.Allergy(
            hospital_id=self.hospital_id,
            status="active",
            **data.model_dump(),
        )
        self.db.add(allergy)
        await self.db.flush()
        return allergy

    async def get_patient_allergies(self, patient_id: uuid.UUID) -> list[models.Allergy]:
        result = await self.db.execute(
            select(models.Allergy).where(
                models.Allergy.patient_id == patient_id,
                models.Allergy.hospital_id == self.hospital_id,
                models.Allergy.status == "active",
            )
        )
        return list(result.scalars().all())


class ClinicalNoteService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None,
                 user_name: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id
        self.user_name = user_name

    async def create_note(self, data: schemas.ClinicalNoteCreate) -> models.ClinicalNote:
        patient_id = await self.db.scalar(
            select(models.Patient.id).where(
                models.Patient.id == data.patient_id,
                models.Patient.hospital_id == self.hospital_id,
                models.Patient.is_active.is_(True),
            )
        )
        if patient_id is None:
            raise LookupError("Patient not found at this facility")
        if data.encounter_id is not None:
            encounter_id = await self.db.scalar(
                select(models.Encounter.id).where(
                    models.Encounter.id == data.encounter_id,
                    models.Encounter.patient_id == patient_id,
                    models.Encounter.hospital_id == self.hospital_id,
                )
            )
            if encounter_id is None:
                raise LookupError("Encounter not found for this patient")
        note = models.ClinicalNote(
            hospital_id=self.hospital_id,
            created_by=self.user_id,
            authored_by=(self.user_name or self.user_id or "Clinical team")[:200],
            authored_datetime=datetime.now(timezone.utc).replace(tzinfo=None),
            **data.model_dump(exclude={"authored_by", "authored_datetime"}),
        )
        self.db.add(note)
        await self.db.flush()
        return note

    async def get_note(self, note_id: uuid.UUID) -> Optional[models.ClinicalNote]:
        result = await self.db.execute(
            select(models.ClinicalNote).where(
                models.ClinicalNote.id == note_id,
                models.ClinicalNote.hospital_id == self.hospital_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_notes(
        self,
        patient_id: Optional[uuid.UUID] = None,
        encounter_id: Optional[uuid.UUID] = None,
        note_type: Optional[str] = None,
        author: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.ClinicalNote], int]:
        stmt = select(models.ClinicalNote).where(
            models.ClinicalNote.hospital_id == self.hospital_id
        )
        if patient_id:
            stmt = stmt.where(models.ClinicalNote.patient_id == patient_id)
        if encounter_id:
            stmt = stmt.where(models.ClinicalNote.encounter_id == encounter_id)
        if note_type:
            stmt = stmt.where(models.ClinicalNote.note_type == note_type)
        if author:
            stmt = stmt.where(models.ClinicalNote.authored_by.ilike(f"%{author}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(models.ClinicalNote.authored_datetime.desc())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_note(
        self, note_id: uuid.UUID, data: schemas.ClinicalNoteUpdate
    ) -> Optional[models.ClinicalNote]:
        note = await self.get_note(note_id)
        if not note:
            return None
        if note.status == models.NoteStatus.final and data.status != models.NoteStatus.amended:
            raise ValueError("Cannot modify a finalized note")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return note
        for field, value in update_data.items():
            if field in ("status", "is_confidential") and value is None:
                raise ValueError(f"{field} cannot be null")
            setattr(note, field, value)
        note.updated_by = self.user_id
        await self.db.flush()
        await self.db.refresh(note)
        return note

    async def finalize_note(self, note_id: uuid.UUID) -> Optional[models.ClinicalNote]:
        return await self.update_note(
            note_id,
            schemas.ClinicalNoteUpdate(status=models.NoteStatus.final),
        )


class OrderService:
    LAB_TRANSITIONS = {
        models.OrderStatus.ordered: {models.OrderStatus.collected, models.OrderStatus.cancelled},
        models.OrderStatus.collected: {models.OrderStatus.received, models.OrderStatus.cancelled},
        models.OrderStatus.received: {models.OrderStatus.in_progress, models.OrderStatus.cancelled},
        models.OrderStatus.in_progress: {models.OrderStatus.resulted, models.OrderStatus.cancelled},
        models.OrderStatus.resulted: {models.OrderStatus.verified},
        models.OrderStatus.verified: set(),
        models.OrderStatus.cancelled: set(),
    }

    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def create_order(self, data: schemas.OrderCreate) -> models.Order:
        patient = await self.db.scalar(
            select(models.Patient.id).where(
                models.Patient.id == data.patient_id,
                models.Patient.hospital_id == self.hospital_id,
                models.Patient.deleted_at.is_(None),
            )
        )
        if patient is None:
            raise LookupError("Patient not found")
        if data.encounter_id:
            encounter = await self.db.scalar(
                select(models.Encounter.id).where(
                    models.Encounter.id == data.encounter_id,
                    models.Encounter.patient_id == data.patient_id,
                    models.Encounter.hospital_id == self.hospital_id,
                )
            )
            if encounter is None:
                raise ValueError("Encounter does not belong to this patient and hospital")
        order = models.Order(
            hospital_id=self.hospital_id,
            status=models.OrderStatus.ordered,
            ordered_by=self.user_id,
            ordered_datetime=datetime.utcnow(),
            **data.model_dump(),
        )
        self.db.add(order)
        await self.db.flush()
        return order

    async def get_order(self, order_id: uuid.UUID) -> Optional[models.Order]:
        result = await self.db.execute(
            select(models.Order)
            .where(models.Order.id == order_id, models.Order.hospital_id == self.hospital_id)
            .options(selectinload(models.Order.results))
        )
        return result.scalar_one_or_none()

    async def list_orders(
        self,
        patient_id: Optional[uuid.UUID] = None,
        status: Optional[models.OrderStatus] = None,
        order_type: Optional[models.OrderType] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.Order], int]:
        stmt = select(models.Order).where(models.Order.hospital_id == self.hospital_id)
        if patient_id:
            stmt = stmt.where(models.Order.patient_id == patient_id)
        if status:
            stmt = stmt.where(models.Order.status == status)
        if order_type:
            stmt = stmt.where(models.Order.order_type == order_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(models.Order.ordered_datetime.desc().nullslast())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def cancel_order(self, order_id: uuid.UUID) -> Optional[models.Order]:
        order = await self._get_order_for_update(order_id)
        if order is None:
            return None
        self._assert_transition(order, models.OrderStatus.cancelled)
        order.status = models.OrderStatus.cancelled
        await self.db.flush()
        return order

    async def collect_specimen(
        self, order_id: uuid.UUID, data: schemas.SpecimenCollection
    ) -> Optional[models.Order]:
        order = await self._get_order_for_update(order_id)
        if order is None:
            return None
        self._assert_lab_order(order)
        self._assert_transition(order, models.OrderStatus.collected)
        if data.specimen_type and order.specimen_type and data.specimen_type != order.specimen_type:
            raise ValueError("Collected specimen type does not match the requested specimen type")
        duplicate = await self.db.scalar(
            select(models.Order.id).where(
                models.Order.hospital_id == self.hospital_id,
                models.Order.specimen_id == data.specimen_id,
                models.Order.id != order.id,
            )
        )
        if duplicate is not None:
            raise ValueError("Specimen ID is already assigned to another order")
        order.specimen_type = data.specimen_type or order.specimen_type
        order.specimen_id = data.specimen_id
        order.collected_by = self.user_id
        order.collected_datetime = data.collected_datetime or datetime.utcnow()
        order.status = models.OrderStatus.collected
        await self.db.flush()
        return order

    async def receive_specimen(
        self, order_id: uuid.UUID, data: schemas.SpecimenReceipt
    ) -> Optional[models.Order]:
        order = await self._get_order_for_update(order_id)
        if order is None:
            return None
        self._assert_lab_order(order)
        self._assert_transition(order, models.OrderStatus.received)
        order.received_by = self.user_id
        order.received_datetime = data.received_datetime or datetime.utcnow()
        order.status = models.OrderStatus.received
        await self.db.flush()
        return order

    async def start_processing(self, order_id: uuid.UUID) -> Optional[models.Order]:
        order = await self._get_order_for_update(order_id)
        if order is None:
            return None
        self._assert_lab_order(order)
        self._assert_transition(order, models.OrderStatus.in_progress)
        order.status = models.OrderStatus.in_progress
        order.performed_by = self.user_id
        order.performed_datetime = datetime.utcnow()
        await self.db.flush()
        return order

    async def add_result(self, data: schemas.ResultCreate) -> models.Result:
        order = await self._get_order_for_update(data.order_id)
        if order is None:
            raise LookupError("Order not found")
        self._assert_lab_order(order)
        if order.status not in {models.OrderStatus.received, models.OrderStatus.in_progress}:
            raise ValueError("Results can only be entered for a received or in-progress order")
        if data.patient_id != order.patient_id:
            raise ValueError("Result patient_id does not match the order patient")
        result = models.Result(
            hospital_id=self.hospital_id,
            performed_by=self.user_id or data.performed_by,
            performed_datetime=data.performed_datetime or datetime.utcnow(),
            **data.model_dump(exclude={"performed_by", "performed_datetime"}),
        )
        self.db.add(result)
        # Materialize the UUID before linking it from the order.
        await self.db.flush()
        order.status = models.OrderStatus.resulted
        order.result_id = result.id
        order.performed_by = result.performed_by
        order.performed_datetime = result.performed_datetime
        await self.db.flush()
        return result

    async def verify_results(self, order_id: uuid.UUID) -> Optional[models.Order]:
        order = await self._get_order_for_update(order_id)
        if order is None:
            return None
        self._assert_lab_order(order)
        self._assert_transition(order, models.OrderStatus.verified)
        results = await self.get_order_results(order_id)
        if not results:
            raise ValueError("An order without results cannot be verified")
        verified_at = datetime.utcnow()
        for result in results:
            result.verified_by = self.user_id
            result.verified_datetime = verified_at
        order.status = models.OrderStatus.verified
        order.verified_by = self.user_id
        order.verified_datetime = verified_at
        await self.db.flush()
        return order

    async def get_order_results(self, order_id: uuid.UUID) -> list[models.Result]:
        result = await self.db.execute(
            select(models.Result).where(
                models.Result.order_id == order_id,
                models.Result.hospital_id == self.hospital_id,
            )
        )
        return list(result.scalars().all())

    async def _get_order_for_update(self, order_id: uuid.UUID) -> Optional[models.Order]:
        result = await self.db.execute(
            select(models.Order).where(
                models.Order.id == order_id,
                models.Order.hospital_id == self.hospital_id,
            ).with_for_update()
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _assert_lab_order(order: models.Order) -> None:
        if order.order_type != models.OrderType.lab:
            raise ValueError("This workflow action is only valid for laboratory orders")

    def _assert_transition(self, order: models.Order, target: models.OrderStatus) -> None:
        if target not in self.LAB_TRANSITIONS.get(order.status, set()):
            raise ValueError(f"Invalid order status transition: {order.status.value} -> {target.value}")


class ImmunizationService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def add_immunization(self, data: schemas.ImmunizationCreate) -> models.Immunization:
        imm = models.Immunization(
            hospital_id=self.hospital_id,
            **data.model_dump(),
        )
        self.db.add(imm)
        await self.db.flush()
        return imm

    async def get_patient_immunizations(self, patient_id: uuid.UUID) -> list[models.Immunization]:
        result = await self.db.execute(
            select(models.Immunization)
            .where(
                models.Immunization.patient_id == patient_id,
                models.Immunization.hospital_id == self.hospital_id,
            )
            .order_by(models.Immunization.administered_date.desc())
        )
        return list(result.scalars().all())


class ProblemListService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def add_problem(self, data: schemas.ProblemCreate) -> models.ProblemList:
        problem = models.ProblemList(
            hospital_id=self.hospital_id,
            **data.model_dump(),
        )
        self.db.add(problem)
        await self.db.flush()
        return problem

    async def get_active_problems(self, patient_id: uuid.UUID) -> list[models.ProblemList]:
        result = await self.db.execute(
            select(models.ProblemList).where(
                models.ProblemList.patient_id == patient_id,
                models.ProblemList.hospital_id == self.hospital_id,
                models.ProblemList.status == models.ProblemStatus.active,
            )
        )
        return list(result.scalars().all())


class SocialHistoryService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def add_social_history(self, data: schemas.SocialHistoryCreate) -> models.SocialHistory:
        sh = models.SocialHistory(hospital_id=self.hospital_id, **data.model_dump())
        self.db.add(sh)
        await self.db.flush()
        return sh

    async def get_patient_social_history(self, patient_id: uuid.UUID) -> list[models.SocialHistory]:
        result = await self.db.execute(
            select(models.SocialHistory).where(
                models.SocialHistory.patient_id == patient_id,
                models.SocialHistory.hospital_id == self.hospital_id,
            )
        )
        return list(result.scalars().all())


class FamilyHistoryService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def add_family_history(self, data: schemas.FamilyHistoryCreate) -> models.FamilyHistory:
        fh = models.FamilyHistory(hospital_id=self.hospital_id, **data.model_dump())
        self.db.add(fh)
        await self.db.flush()
        return fh

    async def get_patient_family_history(self, patient_id: uuid.UUID) -> list[models.FamilyHistory]:
        result = await self.db.execute(
            select(models.FamilyHistory).where(
                models.FamilyHistory.patient_id == patient_id,
                models.FamilyHistory.hospital_id == self.hospital_id,
            )
        )
        return list(result.scalars().all())


class FHIRConverter:
    @staticmethod
    def patient_to_fhir(patient: models.Patient) -> dict:
        name = [{"use": "official", "family": patient.last_name, "given": [patient.first_name]}]
        if patient.middle_name:
            name[0]["given"].append(patient.middle_name)
        identifier = []
        if patient.nrc_number:
            identifier.append({
                "system": "https://fhir.ubuntucare.zm/identifier/nrc",
                "value": patient.nrc_number,
            })
        if patient.smartcare_id:
            identifier.append({
                "system": "https://fhir.ubuntucare.zm/identifier/smartcare",
                "value": patient.smartcare_id,
            })
        return {
            "resourceType": "Patient",
            "id": str(patient.id),
            "identifier": identifier,
            "active": patient.is_active,
            "name": name,
            "gender": patient.gender.value,
            "birthDate": patient.date_of_birth.isoformat(),
            "maritalStatus": {"text": patient.marital_status.value} if patient.marital_status else None,
            "telecom": [
                {"system": "phone", "value": patient.phone, "use": "mobile"},
            ],
            "address": [
                {
                    "line": [patient.address_line] if patient.address_line else [],
                    "city": patient.city or "",
                    "district": patient.district or "",
                    "state": patient.province.value if patient.province else "",
                }
            ],
            "managingOrganization": {"reference": f"Organization/{patient.hospital_id}"},
        }

    @staticmethod
    def encounter_to_fhir(encounter: models.Encounter) -> dict:
        return {
            "resourceType": "Encounter",
            "id": str(encounter.id),
            "status": encounter.status.value,
            "class": {"code": encounter.encounter_type.value, "system": "http://hl7.org/fhir/v3/ActCode"},
            "subject": {"reference": f"Patient/{encounter.patient_id}"},
            "period": {
                "start": encounter.encounter_datetime.isoformat(),
            },
            "reasonCode": [{"text": encounter.chief_complaint}] if encounter.chief_complaint else [],
            "diagnosis": [],
        }
