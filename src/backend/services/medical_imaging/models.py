from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base
from src.backend.mixins import AuditMixin, TenantMixin


class ImagingModality(str, enum.Enum):
    cxr = "Chest X-Ray"
    msk_xr = "Musculoskeletal X-Ray"
    abdominal_xr = "Abdominal X-Ray"
    ct_head = "CT Head"
    ct_chest = "CT Chest"
    ct_abdomen = "CT Abdomen"
    mri_brain = "MRI Brain"
    mri_spine = "MRI Spine"
    ultrasound_abdomen = "Ultrasound Abdomen"
    ultrasound_obstetric = "Ultrasound Obstetric"
    echocardiogram = "Echocardiogram"
    mammography = "Mammography"
    fluoroscopy = "Fluoroscopy"
    nuclear_medicine = "Nuclear Medicine"


class StudyStatus(str, enum.Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    reported = "reported"
    cancelled = "cancelled"


class ImagingStudy(Base, AuditMixin, TenantMixin):
    __tablename__ = "imaging_studies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(255))
    modality: Mapped[ImagingModality] = mapped_column(Enum(ImagingModality), nullable=False)
    body_part: Mapped[Optional[str]] = mapped_column(String(200))
    study_description: Mapped[Optional[str]] = mapped_column(Text)
    study_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[StudyStatus] = mapped_column(Enum(StudyStatus), default=StudyStatus.scheduled)
    accession_number: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    dicom_study_uid: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    referring_physician: Mapped[Optional[str]] = mapped_column(String(200))
    interpreting_physician: Mapped[Optional[str]] = mapped_column(String(200))
    modality_technician: Mapped[Optional[str]] = mapped_column(String(200))
    facility_name: Mapped[Optional[str]] = mapped_column(String(200))
    clinical_history: Mapped[Optional[str]] = mapped_column(Text)
    findings_summary: Mapped[Optional[str]] = mapped_column(Text)
    impression: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    images = relationship("Image", back_populates="study")
    reports = relationship("RadiologyReport", back_populates="study")
    ai_findings = relationship("AIFinding", back_populates="study")

    __table_args__ = (
        Index("idx_imaging_study_patient", "patient_id", "study_date"),
        Index("idx_imaging_study_modality", "modality", "study_date"),
    )


class Image(Base, AuditMixin, TenantMixin):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imaging_studies.id"), nullable=False, index=True
    )
    instance_number: Mapped[Optional[int]] = mapped_column(Integer)
    sop_instance_uid: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    dicom_file_url: Mapped[Optional[str]] = mapped_column(String(500))
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    image_width: Mapped[Optional[int]] = mapped_column(Integer)
    image_height: Mapped[Optional[int]] = mapped_column(Integer)
    bits_allocated: Mapped[Optional[int]] = mapped_column(Integer)
    pixel_representation: Mapped[Optional[int]] = mapped_column(Integer)
    image_format: Mapped[str] = mapped_column(String(20), default="DICOM")
    storage_path: Mapped[Optional[str]] = mapped_column(String(500))

    study = relationship("ImagingStudy", back_populates="images")


class RadiologyReport(Base, AuditMixin, TenantMixin):
    __tablename__ = "radiology_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imaging_studies.id"), nullable=False, index=True
    )
    report_title: Mapped[Optional[str]] = mapped_column(String(500))
    clinical_indication: Mapped[Optional[str]] = mapped_column(Text)
    technique: Mapped[Optional[str]] = mapped_column(Text)
    comparison: Mapped[Optional[str]] = mapped_column(Text)
    findings: Mapped[Optional[str]] = mapped_column(Text)
    impression: Mapped[Optional[str]] = mapped_column(Text)
    recommendation: Mapped[Optional[str]] = mapped_column(Text)
    report_status: Mapped[str] = mapped_column(String(20), default="draft")
    reported_by: Mapped[Optional[str]] = mapped_column(String(200))
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    transcribed_by: Mapped[Optional[str]] = mapped_column(String(200))
    verified_by: Mapped[Optional[str]] = mapped_column(String(200))
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    study = relationship("ImagingStudy", back_populates="reports")


class AIFinding(Base, AuditMixin, TenantMixin):
    __tablename__ = "ai_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imaging_studies.id"), nullable=False, index=True
    )
    finding_type: Mapped[str] = mapped_column(String(100), nullable=False)
    finding_description: Mapped[Optional[str]] = mapped_column(Text)
    confidence_score: Mapped[Optional[float]] = mapped_column(default=0.0)
    bounding_box: Mapped[Optional[dict]] = mapped_column(Text)
    segmentation_mask_url: Mapped[Optional[str]] = mapped_column(String(500))
    model_name: Mapped[Optional[str]] = mapped_column(String(200))
    model_version: Mapped[Optional[str]] = mapped_column(String(50))
    is_reviewed: Mapped[bool] = mapped_column(default=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(200))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_positive: Mapped[Optional[bool]]
    notes: Mapped[Optional[str]] = mapped_column(Text)

    study = relationship("ImagingStudy", back_populates="ai_findings")

    __table_args__ = (
        Index("idx_ai_finding_type", "finding_type", "confidence_score"),
    )
