from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.services.laboratory.models import LabOrder, LabResult, LabStatus, LabTest, SpecimenType, TestResultFlag

logger = logging.getLogger(__name__)

ZAMBIA_TEST_CATALOG: list[dict[str, Any]] = [
    {"code": "MAL_RDT", "name": "Malaria RDT", "category": "Parasitology", "specimen": "blood"},
    {"code": "MAL_BLOOD_FILM", "name": "Malaria Blood Film", "category": "Parasitology", "specimen": "blood"},
    {"code": "HIV_RDT", "name": "HIV Rapid Test", "category": "Serology", "specimen": "blood"},
    {"code": "HIV_VL", "name": "HIV Viral Load", "category": "Molecular", "specimen": "blood"},
    {"code": "CD4_COUNT", "name": "CD4 Count", "category": "Immunology", "specimen": "blood"},
    {"code": "TB_GXPERT", "name": "TB GeneXpert", "category": "Molecular", "specimen": "sputum"},
    {"code": "TB_SMEAR", "name": "TB AFB Smear", "category": "Microbiology", "specimen": "sputum"},
    {"code": "TB_CULTURE", "name": "TB Culture", "category": "Microbiology", "specimen": "sputum"},
    {"code": "FBC", "name": "Full Blood Count", "category": "Hematology", "specimen": "blood"},
    {"code": "HB", "name": "Hemoglobin", "category": "Hematology", "specimen": "blood"},
    {"code": "RBS", "name": "Random Blood Sugar", "category": "Chemistry", "specimen": "blood"},
    {"code": "FBS", "name": "Fasting Blood Sugar", "category": "Chemistry", "specimen": "blood"},
    {"code": "UFR", "name": "Urinalysis", "category": "Chemistry", "specimen": "urine"},
    {"code": "RFT", "name": "Renal Function Test", "category": "Chemistry", "specimen": "blood"},
    {"code": "LFT", "name": "Liver Function Test", "category": "Chemistry", "specimen": "blood"},
    {"code": "CHOL", "name": "Cholesterol", "category": "Chemistry", "specimen": "blood"},
    {"code": "SYPH_RPR", "name": "Syphilis RPR", "category": "Serology", "specimen": "blood"},
    {"code": "HPV_DNA", "name": "HPV DNA Test", "category": "Molecular", "specimen": "swab"},
    {"code": "PREGNANCY_HCG", "name": "Pregnancy Test (hCG)", "category": "Serology", "specimen": "urine"},
    {"code": "CHOLERA_STOOL", "name": "Cholera Stool Culture", "category": "Microbiology", "specimen": "stool"},
    {"code": "TYPHOID_WIDAL", "name": "Typhoid Widal Test", "category": "Serology", "specimen": "blood"},
    {"code": "HEP_B_SAG", "name": "Hepatitis B Surface Antigen", "category": "Serology", "specimen": "blood"},
    {"code": "HEP_C_AB", "name": "Hepatitis C Antibody", "category": "Serology", "specimen": "blood"},
    {"code": "CRP", "name": "C-Reactive Protein", "category": "Chemistry", "specimen": "blood"},
    {"code": "BLOOD_CULTURE", "name": "Blood Culture", "category": "Microbiology", "specimen": "blood"},
    {"code": "URINE_CULTURE", "name": "Urine Culture & Sensitivity", "category": "Microbiology", "specimen": "urine"},
    {"code": "SPUTUM_CULTURE", "name": "Sputum Culture", "category": "Microbiology", "specimen": "sputum"},
    {"code": "ELECTROLYTES", "name": "Serum Electrolytes", "category": "Chemistry", "specimen": "blood"},
    {"code": "PSA", "name": "Prostate Specific Antigen", "category": "Chemistry", "specimen": "blood"},
    {"code": "BLOOD_GAS", "name": "Blood Gas Analysis", "category": "Chemistry", "specimen": "blood"},
]


class LaboratoryService:
    async def get_zambia_test_catalog(self) -> list[dict[str, Any]]:
        return ZAMBIA_TEST_CATALOG

    # ------------------------------------------------------------------
    # Order processing
    # ------------------------------------------------------------------
    async def create_order(self, session: AsyncSession, data: dict[str, Any]) -> LabOrder:
        order = LabOrder(
            order_number=data.get("order_number", f"LAB-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"),
            patient_id=data["patient_id"],
            encounter_id=data.get("encounter_id"),
            ordering_provider=data.get("ordering_provider"),
            ordering_provider_id=data.get("ordering_provider_id"),
            clinical_notes=data.get("clinical_notes"),
            priority=data.get("priority", "routine"),
            specimen_type=SpecimenType(data["specimen_type"]) if data.get("specimen_type") else None,
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
        )
        session.add(order)
        await session.flush()
        return order

    async def get_order(self, session: AsyncSession, order_id: str) -> LabOrder | None:
        result = await session.execute(select(LabOrder).where(LabOrder.id == order_id))
        return result.scalar_one_or_none()

    async def search_orders(
        self, session: AsyncSession, patient_id: str | None = None,
        status: str | None = None, date_from: datetime | None = None,
        date_to: datetime | None = None, limit: int = 100,
    ) -> list[LabOrder]:
        query = select(LabOrder)
        if patient_id:
            query = query.where(LabOrder.patient_id == patient_id)
        if status:
            query = query.where(LabOrder.status == LabStatus(status))
        if date_from:
            query = query.where(LabOrder.order_date >= date_from)
        if date_to:
            query = query.where(LabOrder.order_date <= date_to)
        query = query.order_by(LabOrder.order_date.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def update_order_status(
        self, session: AsyncSession, order_id: str, status: str,
        **extra: Any,
    ) -> LabOrder | None:
        result = await session.execute(select(LabOrder).where(LabOrder.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return None
        order.status = LabStatus(status)
        for key, value in extra.items():
            if hasattr(order, key):
                setattr(order, key, value)
        await session.flush()
        return order

    # ------------------------------------------------------------------
    # Result entry
    # ------------------------------------------------------------------
    async def enter_result(self, session: AsyncSession, data: dict[str, Any]) -> LabResult:
        flag = TestResultFlag.normal
        result_value = data.get("result_value", "")

        if data.get("is_critical"):
            flag = TestResultFlag.critical_high if data.get("result_numeric", 0) > 0 else TestResultFlag.critical_low
        elif data.get("is_abnormal"):
            flag = TestResultFlag.abnormal

        lab_result = LabResult(
            order_id=data["order_id"],
            test_code=data["test_code"],
            test_name=data.get("test_name", ""),
            result_value=result_value,
            result_numeric=data.get("result_numeric"),
            unit=data.get("unit"),
            reference_range_low=data.get("reference_range_low"),
            reference_range_high=data.get("reference_range_high"),
            flag=flag,
            specimen_type=data.get("specimen_type"),
            result_date=data.get("result_date", datetime.now(timezone.utc)),
            performed_by=data.get("performed_by"),
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
            is_abnormal=data.get("is_abnormal", False),
            is_critical=data.get("is_critical", False),
        )
        session.add(lab_result)
        await session.flush()

        await self.update_order_status(session, data["order_id"], "completed")
        return lab_result

    async def get_results_for_order(
        self, session: AsyncSession, order_id: str,
    ) -> list[LabResult]:
        result = await session.execute(
            select(LabResult).where(LabResult.order_id == order_id)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Critical value alerting
    # ------------------------------------------------------------------
    async def get_critical_results(
        self, session: AsyncSession, hours: int = 24,
    ) -> list[LabResult]:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await session.execute(
            select(LabResult).where(
                LabResult.is_critical == True,
                LabResult.result_date >= since,
            ).order_by(LabResult.result_date.desc())
        )
        return list(result.scalars().all())

    async def get_abnormal_results(
        self, session: AsyncSession, patient_id: str | None = None,
        date_from: datetime | None = None, limit: int = 50,
    ) -> list[LabResult]:
        query = select(LabResult).where(LabResult.is_abnormal == True)
        if patient_id:
            query = query.join(LabOrder).where(LabOrder.patient_id == patient_id)
        if date_from:
            query = query.where(LabResult.result_date >= date_from)
        query = query.order_by(LabResult.result_date.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Lab machine interface (HL7 placeholder)
    # ------------------------------------------------------------------
    async def process_hl7_message(self, message: str) -> dict[str, Any]:
        logger.info("HL7 message received: %s", message[:200])
        return {"parsed": True, "segments": message.count("|")}


laboratory_service = LaboratoryService()
