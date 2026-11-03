from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.services.medical_imaging.models import AIFinding, Image, ImagingModality, ImagingStudy, RadiologyReport, StudyStatus

logger = logging.getLogger(__name__)


class MedicalImagingService:
    async def create_study(self, session: AsyncSession, data: dict[str, Any]) -> ImagingStudy:
        study = ImagingStudy(
            patient_id=data["patient_id"],
            order_id=data.get("order_id"),
            modality=ImagingModality(data["modality"]),
            body_part=data.get("body_part"),
            study_description=data.get("study_description"),
            study_date=data.get("study_date", datetime.now(timezone.utc)),
            accession_number=data.get("accession_number", str(uuid.uuid4())),
            dicom_study_uid=data.get("dicom_study_uid", str(uuid.uuid4())),
            referring_physician=data.get("referring_physician"),
            modality_technician=data.get("modality_technician"),
            facility_name=data.get("facility_name"),
            clinical_history=data.get("clinical_history"),
            hospital_id=data.get("hospital_id"),
        )
        session.add(study)
        await session.flush()
        return study

    async def get_study(self, session: AsyncSession, study_id: str) -> ImagingStudy | None:
        result = await session.execute(select(ImagingStudy).where(ImagingStudy.id == study_id))
        return result.scalar_one_or_none()

    async def search_studies(
        self, session: AsyncSession, patient_id: str | None = None,
        modality: str | None = None, date_from: datetime | None = None,
        date_to: datetime | None = None, limit: int = 100,
    ) -> list[ImagingStudy]:
        query = select(ImagingStudy)
        if patient_id:
            query = query.where(ImagingStudy.patient_id == patient_id)
        if modality:
            query = query.where(ImagingStudy.modality == ImagingModality(modality))
        if date_from:
            query = query.where(ImagingStudy.study_date >= date_from)
        if date_to:
            query = query.where(ImagingStudy.study_date <= date_to)
        query = query.order_by(ImagingStudy.study_date.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # DICOM processing
    # ------------------------------------------------------------------
    async def process_dicom_file(self, session: AsyncSession, study_id: str, dicom_data: dict[str, Any]) -> Image:
        image = Image(
            study_id=study_id,
            instance_number=dicom_data.get("instance_number"),
            sop_instance_uid=dicom_data.get("sop_instance_uid", str(uuid.uuid4())),
            dicom_file_url=dicom_data.get("file_url"),
            thumbnail_url=dicom_data.get("thumbnail_url"),
            file_size_bytes=dicom_data.get("file_size"),
            image_width=dicom_data.get("width"),
            image_height=dicom_data.get("height"),
            bits_allocated=dicom_data.get("bits_allocated"),
            image_format=dicom_data.get("format", "DICOM"),
            storage_path=dicom_data.get("storage_path"),
            hospital_id=dicom_data.get("hospital_id"),
        )
        session.add(image)
        await session.flush()
        return image

    # ------------------------------------------------------------------
    # Radiology reporting
    # ------------------------------------------------------------------
    async def create_report(self, session: AsyncSession, data: dict[str, Any]) -> RadiologyReport:
        report = RadiologyReport(
            study_id=data["study_id"],
            report_title=data.get("report_title"),
            clinical_indication=data.get("clinical_indication"),
            technique=data.get("technique"),
            comparison=data.get("comparison"),
            findings=data.get("findings"),
            impression=data.get("impression"),
            recommendation=data.get("recommendation"),
            reported_by=data.get("reported_by"),
            hospital_id=data.get("hospital_id"),
        )
        session.add(report)
        await session.flush()

        await self._update_study_status(session, data["study_id"], StudyStatus.reported)
        return report

    async def get_report(self, session: AsyncSession, report_id: str) -> RadiologyReport | None:
        result = await session.execute(select(RadiologyReport).where(RadiologyReport.id == report_id))
        return result.scalar_one_or_none()

    async def _update_study_status(self, session: AsyncSession, study_id: str, status: StudyStatus) -> None:
        result = await session.execute(select(ImagingStudy).where(ImagingStudy.id == study_id))
        study = result.scalar_one_or_none()
        if study:
            study.status = status
            await session.flush()

    # ------------------------------------------------------------------
    # AI findings
    # ------------------------------------------------------------------
    async def add_ai_finding(self, session: AsyncSession, data: dict[str, Any]) -> AIFinding:
        finding = AIFinding(
            study_id=data["study_id"],
            finding_type=data["finding_type"],
            finding_description=data.get("finding_description"),
            confidence_score=data.get("confidence_score", 0.0),
            bounding_box=json.dumps(data.get("bounding_box")),
            segmentation_mask_url=data.get("segmentation_mask_url"),
            model_name=data.get("model_name"),
            model_version=data.get("model_version"),
            is_positive=data.get("is_positive"),
            hospital_id=data.get("hospital_id"),
        )
        session.add(finding)
        await session.flush()
        return finding

    async def get_ai_findings(
        self, session: AsyncSession, study_id: str,
    ) -> list[AIFinding]:
        result = await session.execute(
            select(AIFinding).where(
                AIFinding.study_id == study_id,
            ).order_by(AIFinding.confidence_score.desc())
        )
        return list(result.scalars().all())

    async def review_ai_finding(
        self, session: AsyncSession, finding_id: str, reviewed_by: str,
        is_positive: bool | None = None, notes: str | None = None,
    ) -> AIFinding | None:
        result = await session.execute(select(AIFinding).where(AIFinding.id == finding_id))
        finding = result.scalar_one_or_none()
        if not finding:
            return None
        finding.is_reviewed = True
        finding.reviewed_by = reviewed_by
        finding.reviewed_at = datetime.now(timezone.utc)
        if is_positive is not None:
            finding.is_positive = is_positive
        if notes:
            finding.notes = notes
        await session.flush()
        return finding

    # ------------------------------------------------------------------
    # Chest X-ray analysis (TB, pneumonia)
    # ------------------------------------------------------------------
    async def analyze_chest_xray(
        self, session: AsyncSession, study_id: str,
    ) -> list[dict[str, Any]]:
        study = await self.get_study(session, study_id)
        if not study:
            return []
        results = []
        tb_finding = await self.add_ai_finding(session, {
            "study_id": study_id,
            "finding_type": "tuberculosis",
            "finding_description": "Chest X-ray analysis for TB suggestive findings",
            "confidence_score": 0.0,
            "model_name": "chest-xray-tb-detection",
            "model_version": "v1",
            "hospital_id": study.hospital_id,
        })
        results.append(tb_finding)

        pneumonia_finding = await self.add_ai_finding(session, {
            "study_id": study_id,
            "finding_type": "pneumonia",
            "finding_description": "Chest X-ray analysis for pneumonic consolidation",
            "confidence_score": 0.0,
            "model_name": "chest-xray-pneumonia-detection",
            "model_version": "v1",
            "hospital_id": study.hospital_id,
        })
        results.append(pneumonia_finding)
        return results

    # ------------------------------------------------------------------
    # PACS integration
    # ------------------------------------------------------------------
    async def send_to_pacs(self, study_id: str) -> bool:
        try:
            logger.info("Study %s sent to PACS (placeholder)", study_id)
            return True
        except Exception as e:
            logger.error("PACS send failed: %s", e)
            return False


medical_imaging_service = MedicalImagingService()
