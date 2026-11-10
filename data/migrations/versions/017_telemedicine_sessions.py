"""Create telemedicine consultation, waiting-room, recording and prescription tables.

Revision ID: 017
Revises: 016
"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "017"
down_revision: Optional[str] = "016"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


consultation_type = postgresql.ENUM(
    "video", "audio", "chat", "phone", name="consultationtype", create_type=False
)
consultation_status = postgresql.ENUM(
    "scheduled",
    "in_waiting_room",
    "in_progress",
    "completed",
    "cancelled",
    "no_show",
    name="consultationstatus",
    create_type=False,
)
recording_status = postgresql.ENUM(
    "recording", "completed", "failed", "deleted", name="recordingstatus", create_type=False
)
prescription_status = postgresql.ENUM(
    "draft", "signed", "dispensed", "cancelled", name="prescriptionstatus", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        consultation_type,
        consultation_status,
        recording_status,
        prescription_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "teleconsultations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("consultation_type", consultation_type, nullable=False),
        sa.Column("status", consultation_status, nullable=False, server_default="scheduled"),
        sa.Column("scheduled_start", sa.DateTime(), nullable=True),
        sa.Column("actual_start", sa.DateTime(), nullable=True),
        sa.Column("actual_end", sa.DateTime(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("treatment_plan", sa.Text(), nullable=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
    )
    op.create_index("ix_teleconsultations_hospital_id", "teleconsultations", ["hospital_id"])
    op.create_index("ix_teleconsultations_patient_id", "teleconsultations", ["patient_id"])
    op.create_index("ix_teleconsultations_provider_id", "teleconsultations", ["provider_id"])
    op.create_index("idx_teleconsult_provider_status", "teleconsultations", ["provider_id", "status"])
    op.create_index("idx_teleconsult_patient", "teleconsultations", ["patient_id", "scheduled_start"])

    op.create_table(
        "waiting_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
        sa.Column(
            "consultation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teleconsultations.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("patient_joined_at", sa.DateTime(), nullable=True),
        sa.Column("provider_joined_at", sa.DateTime(), nullable=True),
        sa.Column("invite_token_hash", sa.String(64), nullable=False),
        sa.Column("invite_expires_at", sa.DateTime(), nullable=False),
        sa.Column("room_sid", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_waiting_rooms_hospital_id", "waiting_rooms", ["hospital_id"])

    op.create_table(
        "recordings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "consultation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teleconsultations.id"),
            nullable=False,
        ),
        sa.Column("recording_type", sa.String(50), nullable=False),
        sa.Column("file_url", sa.String(1000), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("status", recording_status, nullable=False, server_default="recording"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_recordings_hospital_id", "recordings", ["hospital_id"])
    op.create_index("ix_recordings_consultation_id", "recordings", ["consultation_id"])

    op.create_table(
        "telemedicine_prescriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
        sa.Column(
            "consultation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teleconsultations.id"),
            nullable=False,
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medication_name", sa.String(300), nullable=False),
        sa.Column("generic_name", sa.String(300), nullable=True),
        sa.Column("dosage", sa.String(100), nullable=False),
        sa.Column("frequency", sa.String(200), nullable=False),
        sa.Column("duration", sa.String(100), nullable=False),
        sa.Column("route", sa.String(50), nullable=True),
        sa.Column("quantity", sa.String(50), nullable=True),
        sa.Column("refills", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("status", prescription_status, nullable=False, server_default="draft"),
        sa.Column("signed_by", sa.String(200), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("dispensed_at", sa.DateTime(), nullable=True),
        sa.Column("is_controlled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pharmacy_notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_telemedicine_prescriptions_hospital_id", "telemedicine_prescriptions", ["hospital_id"])
    op.create_index("ix_telemedicine_prescriptions_consultation_id", "telemedicine_prescriptions", ["consultation_id"])
    op.create_index("ix_telemedicine_prescriptions_patient_id", "telemedicine_prescriptions", ["patient_id"])


def downgrade() -> None:
    op.drop_table("telemedicine_prescriptions")
    op.drop_table("recordings")
    op.drop_table("waiting_rooms")
    op.drop_table("teleconsultations")
    for enum_type in (
        prescription_status,
        recording_status,
        consultation_status,
        consultation_type,
    ):
        enum_type.drop(op.get_bind(), checkfirst=True)
