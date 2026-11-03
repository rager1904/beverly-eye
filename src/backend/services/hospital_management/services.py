import logging
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.config import settings

from . import models, schemas

logger = logging.getLogger(__name__)


class HospitalService:
    def __init__(self, db: AsyncSession, hospital_id: Optional[uuid.UUID] = None, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def get_hospital(self) -> Optional[models.Hospital]:
        if not self.hospital_id:
            return None
        result = await self.db.execute(
            select(models.Hospital).where(
                models.Hospital.id == self.hospital_id,
                models.Hospital.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def create_hospital(self, data: schemas.HospitalCreate) -> models.Hospital:
        hospital = models.Hospital(**data.model_dump(), created_by=self.user_id)
        self.db.add(hospital)
        await self.db.flush()
        return hospital

    async def list_hospitals(self) -> list[models.Hospital]:
        result = await self.db.execute(
            select(models.Hospital).where(
                models.Hospital.is_active == True,
            ).order_by(models.Hospital.name)
        )
        return list(result.scalars().all())

    async def get_departments(self, include_inactive: bool = False) -> list[models.Department]:
        stmt = select(models.Department).where(
            models.Department.hospital_id == self.hospital_id,
        )
        if not include_inactive:
            stmt = stmt.where(models.Department.is_active == True)
        stmt = stmt.order_by(models.Department.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_department(self, data: schemas.DepartmentCreate) -> models.Department:
        dept = models.Department(hospital_id=self.hospital_id, created_by=self.user_id, **data.model_dump())
        self.db.add(dept)
        await self.db.flush()
        return dept

    async def get_department(self, department_id: uuid.UUID) -> Optional[models.Department]:
        result = await self.db.execute(
            select(models.Department).where(
                models.Department.id == department_id,
                models.Department.hospital_id == self.hospital_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_department(
        self, department_id: uuid.UUID, data: schemas.DepartmentUpdate
    ) -> models.Department:
        dept = await self.get_department(department_id)
        if dept is None:
            raise LookupError("Department not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(dept, field, value)
        dept.updated_by = self.user_id
        await self.db.flush()
        return dept

    async def deactivate_department(self, department_id: uuid.UUID) -> models.Department:
        dept = await self.get_department(department_id)
        if dept is None:
            raise LookupError("Department not found")
        dept.is_active = False
        dept.updated_by = self.user_id
        await self.db.flush()
        return dept


class BedManagementService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def get_wards(self) -> list[models.Ward]:
        result = await self.db.execute(
            select(models.Ward).where(
                models.Ward.hospital_id == self.hospital_id,
                models.Ward.is_active == True,
            ).order_by(models.Ward.name)
        )
        return list(result.scalars().all())

    async def admit_patient(self, bed_id: uuid.UUID, data: schemas.AdmissionCreate) -> models.Bed:
        from src.backend.services.emr.models import Patient, Encounter, EncounterType, EncounterStatus

        # Serialize admissions for the same patient, including different beds.
        patient = await self.db.scalar(select(Patient).where(
            Patient.id == data.patient_id, Patient.hospital_id == self.hospital_id,
            Patient.deleted_at.is_(None), Patient.is_active.is_(True),
        ).with_for_update())
        if patient is None:
            raise LookupError("Patient not found")
        existing = await self.db.scalar(select(Encounter.id).where(
            Encounter.patient_id == data.patient_id, Encounter.hospital_id == self.hospital_id,
            Encounter.encounter_type == EncounterType.inpatient,
            Encounter.status.in_([EncounterStatus.planned, EncounterStatus.in_progress, EncounterStatus.on_hold]),
        ).limit(1))
        if existing:
            raise ValueError("Patient already has an active inpatient admission")
        bed = await self.db.scalar(select(models.Bed).where(
            models.Bed.id == bed_id, models.Bed.hospital_id == self.hospital_id,
            models.Bed.is_active.is_(True),
        ).with_for_update())
        if bed is None:
            raise LookupError("Bed not found")
        if bed.status != models.BedStatus.available:
            raise ValueError("Bed is no longer available; select another bed")
        ward = await self.db.scalar(select(models.Ward).where(
            models.Ward.id == bed.ward_id, models.Ward.hospital_id == self.hospital_id,
            models.Ward.is_active.is_(True),
        ).with_for_update())
        if ward is None:
            raise LookupError("Active ward not found")
        if ward.current_occupancy >= ward.capacity:
            raise ValueError("Ward has reached capacity")
        if ward.gender_restriction in {"male", "female"} and patient.gender.value != ward.gender_restriction:
            raise ValueError("Patient does not meet the ward gender restriction")
        encounter = Encounter(
            hospital_id=self.hospital_id, patient_id=data.patient_id,
            encounter_type=EncounterType.inpatient, status=EncounterStatus.in_progress,
            encounter_datetime=datetime.utcnow(), chief_complaint=data.reason,
            triage_notes=data.notes, department=ward.name, provider_id=self.user_id,
            created_by=self.user_id,
        )
        self.db.add(encounter)
        await self.db.flush()
        bed.status = models.BedStatus.occupied
        bed.current_patient_id = patient.id
        bed.current_encounter_id = encounter.id
        bed.occupied_since = encounter.encounter_datetime
        bed.updated_by = self.user_id
        ward.current_occupancy += 1
        await self.db.flush()
        return bed

    async def create_ward(self, data: schemas.WardCreate) -> models.Ward:
        ward = models.Ward(hospital_id=self.hospital_id, current_occupancy=0, created_by=self.user_id, **data.model_dump())
        self.db.add(ward)
        await self.db.flush()
        return ward

    async def get_ward(self, ward_id: uuid.UUID) -> Optional[models.Ward]:
        result = await self.db.execute(
            select(models.Ward).where(
                models.Ward.id == ward_id,
                models.Ward.hospital_id == self.hospital_id,
            )
        )
        ward = result.scalar_one_or_none()
        return ward

    async def get_ward_beds(self, ward_id: uuid.UUID) -> list[models.Bed]:
        result = await self.db.execute(
            select(models.Bed).where(
                models.Bed.ward_id == ward_id,
                models.Bed.hospital_id == self.hospital_id,
                models.Bed.is_active == True,
            ).order_by(models.Bed.bed_label)
        )
        return list(result.scalars().all())

    async def create_bed(self, data: schemas.BedCreate) -> models.Bed:
        ward = await self.get_ward(data.ward_id)
        if not ward:
            raise ValueError("Ward not found")
        bed = models.Bed(hospital_id=self.hospital_id, created_by=self.user_id, **data.model_dump())
        self.db.add(bed)
        await self.db.flush()
        return bed

    async def assign_bed(self, bed_id: uuid.UUID, assignment: schemas.BedAssignment) -> Optional[models.Bed]:
        from src.backend.services.emr.models import Patient, Encounter, EncounterType, EncounterStatus
        patient = await self.db.scalar(select(Patient).where(
            Patient.id == assignment.patient_id, Patient.hospital_id == self.hospital_id,
            Patient.deleted_at.is_(None),
        ).with_for_update())
        if patient is None:
            raise ValueError("Patient not found")
        encounter = await self.db.scalar(select(Encounter).where(
            Encounter.id == assignment.encounter_id, Encounter.patient_id == assignment.patient_id,
            Encounter.hospital_id == self.hospital_id, Encounter.encounter_type == EncounterType.inpatient,
            Encounter.status == EncounterStatus.in_progress,
        ))
        if encounter is None:
            raise ValueError("An active inpatient encounter for this patient is required")
        existing = await self.db.scalar(select(models.Bed.id).where(
            models.Bed.hospital_id == self.hospital_id,
            models.Bed.current_patient_id == assignment.patient_id,
            models.Bed.status == models.BedStatus.occupied,
        ).limit(1))
        if existing:
            raise ValueError("Patient already has an occupied bed")
        bed = await self.db.execute(
            select(models.Bed).where(models.Bed.id == bed_id, models.Bed.hospital_id == self.hospital_id).with_for_update()
        )
        bed = bed.scalar_one_or_none()
        if not bed:
            return None
        if bed.status != models.BedStatus.available:
            raise ValueError(f"Bed is not available (current status: {bed.status.value})")
        bed.status = models.BedStatus.occupied
        bed.current_patient_id = assignment.patient_id
        bed.current_encounter_id = assignment.encounter_id
        bed.occupied_since = datetime.utcnow()
        await self.db.flush()

        await self.db.execute(
            update(models.Ward)
            .where(models.Ward.id == bed.ward_id)
            .values(current_occupancy=models.Ward.current_occupancy + 1)
        )
        await self.db.flush()
        return bed

    async def discharge_bed(self, bed_id: uuid.UUID) -> Optional[models.Bed]:
        bed = await self.db.execute(
            select(models.Bed).where(models.Bed.id == bed_id, models.Bed.hospital_id == self.hospital_id).with_for_update()
        )
        bed = bed.scalar_one_or_none()
        if not bed or bed.status != models.BedStatus.occupied:
            return None
        from src.backend.services.emr.models import Encounter, EncounterStatus
        if bed.current_encounter_id:
            await self.db.execute(update(Encounter).where(
                Encounter.id == bed.current_encounter_id,
                Encounter.hospital_id == self.hospital_id,
            ).values(status=EncounterStatus.discharged, updated_by=self.user_id))
        bed.status = models.BedStatus.available
        bed.current_patient_id = None
        bed.current_encounter_id = None
        bed.occupied_since = None
        await self.db.flush()

        await self.db.execute(
            update(models.Ward)
            .where(models.Ward.id == bed.ward_id)
            .values(current_occupancy=models.Ward.current_occupancy - 1)
        )
        await self.db.flush()
        return bed

    async def get_available_beds(self) -> list[models.Bed]:
        result = await self.db.execute(
            select(models.Bed).where(
                models.Bed.hospital_id == self.hospital_id,
                models.Bed.status == models.BedStatus.available,
                models.Bed.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def get_occupancy_stats(self) -> dict:
        wards = await self.get_wards()
        total_beds = 0
        occupied = sum(w.current_occupancy or 0 for w in wards)

        ward_bed_counts: dict[uuid.UUID, int] = {}
        if wards:
            bed_counts = await self.db.execute(
                select(
                    models.Bed.ward_id,
                    func.count(models.Bed.id),
                ).where(
                    models.Bed.ward_id.in_([w.id for w in wards]),
                    models.Bed.is_active == True,
                ).group_by(models.Bed.ward_id)
            )
            for row in bed_counts:
                ward_bed_counts[row[0]] = row[1]

        total_beds = sum(ward_bed_counts.values())

        return {
            "total_beds": total_beds,
            "occupied": occupied,
            "available": total_beds - occupied,
            "occupancy_rate": round((occupied / total_beds * 100) if total_beds > 0 else 0, 1),
            "ward_breakdown": [
                {
                    "ward_id": str(w.id),
                    "ward_name": w.name,
                    "type": w.ward_type.value,
                    "capacity": w.capacity,
                    "occupancy": w.current_occupancy,
                }
                for w in wards
            ],
        }


class StaffService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def create_staff(self, data: schemas.StaffCreate) -> models.Staff:
        staff = models.Staff(hospital_id=self.hospital_id, created_by=self.user_id, **data.model_dump())
        self.db.add(staff)
        await self.db.flush()
        return staff

    async def get_staff(self, staff_id: uuid.UUID) -> Optional[models.Staff]:
        result = await self.db.execute(
            select(models.Staff).where(
                models.Staff.id == staff_id,
                models.Staff.hospital_id == self.hospital_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_staff(
        self, staff_id: uuid.UUID, data: schemas.StaffUpdate
    ) -> models.Staff:
        staff = await self.get_staff(staff_id)
        if staff is None:
            raise LookupError("Staff member not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(staff, field, value)
        staff.updated_by = self.user_id
        await self.db.flush()
        return staff

    async def deactivate_staff(self, staff_id: uuid.UUID) -> models.Staff:
        staff = await self.get_staff(staff_id)
        if staff is None:
            raise LookupError("Staff member not found")
        staff.is_active = False
        staff.updated_by = self.user_id
        await self.db.flush()
        return staff

    async def list_staff(
        self,
        role: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = True,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.Staff], int]:
        stmt = select(models.Staff).where(
            models.Staff.hospital_id == self.hospital_id,
        )
        if is_active is not None:
            stmt = stmt.where(models.Staff.is_active == is_active)
        if role:
            stmt = stmt.where(models.Staff.role == role)
        if department_id:
            stmt = stmt.where(models.Staff.department_id == department_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(models.Staff.last_name, models.Staff.first_name)
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def add_schedule(self, data: schemas.ScheduleCreate) -> models.StaffSchedule:
        staff = await self.get_staff(data.staff_id)
        if not staff:
            raise ValueError("Staff member not found")
        schedule = models.StaffSchedule(
            hospital_id=self.hospital_id,
            created_by=self.user_id,
            **data.model_dump(),
        )
        self.db.add(schedule)
        await self.db.flush()
        return schedule

    async def get_staff_schedule(
        self, staff_id: uuid.UUID, from_date: date, to_date: date
    ) -> list[models.StaffSchedule]:
        result = await self.db.execute(
            select(models.StaffSchedule).where(
                models.StaffSchedule.staff_id == staff_id,
                models.StaffSchedule.hospital_id == self.hospital_id,
                models.StaffSchedule.shift_date.between(from_date, to_date),
            ).order_by(models.StaffSchedule.shift_date, models.StaffSchedule.start_time)
        )
        return list(result.scalars().all())

    async def get_ward_schedule(
        self, ward_id: uuid.UUID, shift_date: date
    ) -> list[models.StaffSchedule]:
        result = await self.db.execute(
            select(models.StaffSchedule).where(
                models.StaffSchedule.ward_id == ward_id,
                models.StaffSchedule.shift_date == shift_date,
            ).order_by(models.StaffSchedule.start_time)
        )
        return list(result.scalars().all())


class InventoryService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def add_item(self, data: schemas.InventoryCreate) -> models.Inventory:
        item = models.Inventory(hospital_id=self.hospital_id, created_by=self.user_id, **data.model_dump())
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_item(self, item_id: uuid.UUID) -> Optional[models.Inventory]:
        result = await self.db.execute(
            select(models.Inventory).where(
                models.Inventory.id == item_id,
                models.Inventory.hospital_id == self.hospital_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_items(
        self,
        category: Optional[str] = None,
        low_stock_only: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.Inventory], int]:
        stmt = select(models.Inventory).where(
            models.Inventory.hospital_id == self.hospital_id,
            models.Inventory.is_active == True,
        )
        if category:
            stmt = stmt.where(models.Inventory.category == category)
        if low_stock_only:
            stmt = stmt.where(models.Inventory.quantity <= models.Inventory.reorder_level)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(models.Inventory.item_name)
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_stock(self, item_id: uuid.UUID, quantity_change: Decimal) -> Optional[models.Inventory]:
        item = await self.get_item(item_id)
        if not item:
            return None
        new_qty = item.quantity + quantity_change
        await self.db.execute(
            update(models.Inventory)
            .where(models.Inventory.id == item_id)
            .values(quantity=new_qty)
        )
        await self.db.flush()
        return await self.get_item(item_id)


class BillingService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def create_transaction(self, data: schemas.TransactionCreate) -> models.FinancialTransaction:
        total = data.amount_zmw - data.discount_zmw
        txn_number = f"TXN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        txn = models.FinancialTransaction(
            hospital_id=self.hospital_id,
            transaction_number=txn_number,
            total_zmw=total,
            balance_zmw=total,
            payment_status=models.PaymentStatus.pending,
            transaction_date=datetime.utcnow(),
            created_by=self.user_id,
            **data.model_dump(exclude={"discount_zmw", "payment_method"}),
        )
        if data.payment_method:
            txn.payment_method = data.payment_method
        self.db.add(txn)
        await self.db.flush()
        return txn

    async def record_payment(
        self, transaction_id: uuid.UUID, amount_zmw: Decimal, method: Optional[str] = None
    ) -> Optional[models.FinancialTransaction]:
        txn = await self.db.execute(
            select(models.FinancialTransaction).where(
                models.FinancialTransaction.id == transaction_id,
                models.FinancialTransaction.hospital_id == self.hospital_id,
            )
        )
        txn = txn.scalar_one_or_none()
        if not txn:
            return None

        new_paid = txn.paid_amount_zmw + amount_zmw
        new_balance = txn.total_zmw - new_paid

        status = models.PaymentStatus.partial
        if new_balance <= 0:
            status = models.PaymentStatus.paid
            new_balance = Decimal("0")

        receipt = f"RCP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        await self.db.execute(
            update(models.FinancialTransaction)
            .where(models.FinancialTransaction.id == transaction_id)
            .values(
                paid_amount_zmw=new_paid,
                balance_zmw=new_balance,
                payment_status=status,
                receipt_number=receipt,
                payment_method=method if method else txn.payment_method,
            )
        )
        await self.db.flush()
        result = await self.db.execute(
            select(models.FinancialTransaction).where(models.FinancialTransaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def get_patient_bills(self, patient_id: uuid.UUID) -> list[models.FinancialTransaction]:
        result = await self.db.execute(
            select(models.FinancialTransaction).where(
                models.FinancialTransaction.patient_id == patient_id,
                models.FinancialTransaction.hospital_id == self.hospital_id,
            ).order_by(models.FinancialTransaction.transaction_date.desc())
        )
        return list(result.scalars().all())

    async def get_outstanding_balance(self, patient_id: uuid.UUID) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(models.FinancialTransaction.balance_zmw), 0)).where(
                models.FinancialTransaction.patient_id == patient_id,
                models.FinancialTransaction.hospital_id == self.hospital_id,
                models.FinancialTransaction.payment_status.in_(
                    [models.PaymentStatus.pending, models.PaymentStatus.partial]
                ),
            )
        )
        return result.scalar() or Decimal("0")


class NHIMAService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def create_claim(self, data: schemas.ClaimCreate) -> models.InsuranceClaim:
        claim_number = f"NHIMA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        claim = models.InsuranceClaim(
            hospital_id=self.hospital_id,
            claim_number=claim_number,
            created_by=self.user_id,
            **data.model_dump(),
        )
        self.db.add(claim)
        await self.db.flush()
        return claim

    async def submit_claim(self, claim_id: uuid.UUID) -> Optional[models.InsuranceClaim]:
        claim = await self.db.execute(
            select(models.InsuranceClaim).where(
                models.InsuranceClaim.id == claim_id,
                models.InsuranceClaim.hospital_id == self.hospital_id,
            )
        )
        claim = claim.scalar_one_or_none()
        if not claim:
            return None

        claim.status = models.ClaimStatus.submitted
        claim.submission_date = datetime.utcnow()

        if claim.is_nhima:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{settings.nhima_api_url}/claims",
                        json={
                            "claim_number": claim.claim_number,
                            "patient_id": str(claim.patient_id),
                            "diagnosis_codes": claim.diagnosis_codes,
                            "procedure_codes": claim.procedure_codes,
                            "medication_codes": claim.medication_codes,
                            "total_amount": float(claim.total_amount_zmw),
                        },
                        headers={"Authorization": f"Bearer {settings.nhima_api_key}"},
                    )
                    if resp.status_code == 200:
                        claim.status = models.ClaimStatus.processing
                        logger.info(f"NHIMA claim submitted: {claim.claim_number}")
            except Exception as e:
                logger.error(f"NHIMA submission failed: {e}")

        await self.db.flush()
        return claim

    async def get_claims(
        self,
        patient_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.InsuranceClaim], int]:
        stmt = select(models.InsuranceClaim).where(
            models.InsuranceClaim.hospital_id == self.hospital_id
        )
        if patient_id:
            stmt = stmt.where(models.InsuranceClaim.patient_id == patient_id)
        if status:
            stmt = stmt.where(models.InsuranceClaim.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(models.InsuranceClaim.submission_date.desc().nullslast())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total


class EquipmentService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID):
        self.db = db
        self.hospital_id = hospital_id

    async def add_equipment(self, data: schemas.EquipmentCreate) -> models.Equipment:
        equip = models.Equipment(hospital_id=self.hospital_id, **data.model_dump())
        self.db.add(equip)
        await self.db.flush()
        return equip

    async def list_equipment(self, category: Optional[str] = None) -> list[models.Equipment]:
        stmt = select(models.Equipment).where(
            models.Equipment.hospital_id == self.hospital_id,
            models.Equipment.is_active == True,
        )
        if category:
            stmt = stmt.where(models.Equipment.category == category)
        stmt = stmt.order_by(models.Equipment.equipment_name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
