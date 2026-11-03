"""Add patient journeys and journey steps for queueing and referrals.

Revision ID: 009
Revises: 008
Create Date: 2026-10-29
"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "009"
down_revision: Optional[str] = "008"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.create_table(
        "patient_journeys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id"),
            nullable=False,
        ),
        # Plain UUID: the legacy migration schema and ORM models disagree on
        # the encounters table, so a hard foreign key is unsafe.
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("journey_number", sa.String(40), nullable=False),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="waiting"
        ),
        sa.Column(
            "priority", sa.String(20), nullable=False, server_default="routine"
        ),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("arrival_notes", sa.Text(), nullable=True),
        sa.Column("current_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_step_type", sa.String(30), nullable=True),
        sa.Column("current_service_point", sa.String(50), nullable=True),
        sa.Column(
            "current_department_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("current_department_name", sa.String(200), nullable=True),
        sa.Column("current_provider_id", sa.String(50), nullable=True),
        sa.Column("current_provider_name", sa.String(200), nullable=True),
        sa.Column(
            "checked_in_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("closed_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
        sa.Column(
            "hospital_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.UniqueConstraint(
            "hospital_id",
            "journey_number",
            name="uq_patient_journeys_hospital_number",
        ),
    )
    op.create_index(
        "ix_patient_journeys_hospital_id", "patient_journeys", ["hospital_id"]
    )
    op.create_index(
        "ix_patient_journeys_patient_id", "patient_journeys", ["patient_id"]
    )
    op.create_index(
        "ix_patient_journeys_journey_number", "patient_journeys", ["journey_number"]
    )
    op.create_index("ix_patient_journeys_status", "patient_journeys", ["status"])
    op.create_index("ix_patient_journeys_priority", "patient_journeys", ["priority"])
    op.create_index(
        "idx_patient_journeys_patient",
        "patient_journeys",
        ["patient_id", "checked_in_at"],
    )
    op.create_index(
        "idx_patient_journeys_hospital_status",
        "patient_journeys",
        ["hospital_id", "status"],
    )
    op.create_index(
        "idx_patient_journeys_hospital_priority",
        "patient_journeys",
        ["hospital_id", "priority"],
    )

    op.create_table(
        "journey_steps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "journey_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patient_journeys.id"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(30), nullable=False),
        sa.Column("service_point", sa.String(50), nullable=False),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="waiting"
        ),
        sa.Column(
            "priority", sa.String(20), nullable=False, server_default="routine"
        ),
        sa.Column("outcome", sa.String(30), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_name", sa.String(200), nullable=True),
        sa.Column("provider_id", sa.String(50), nullable=True),
        sa.Column("provider_name", sa.String(200), nullable=True),
        sa.Column("queue_position", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("referred_to_step_type", sa.String(30), nullable=True),
        sa.Column("referred_to_service_point", sa.String(50), nullable=True),
        sa.Column(
            "referred_to_department_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("referred_to_provider_id", sa.String(50), nullable=True),
        sa.Column("called_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
        sa.Column(
            "hospital_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.UniqueConstraint(
            "journey_id", "step_number", name="uq_journey_steps_journey_number"
        ),
    )
    op.create_index(
        "ix_journey_steps_hospital_id", "journey_steps", ["hospital_id"]
    )
    op.create_index("ix_journey_steps_journey_id", "journey_steps", ["journey_id"])
    op.create_index("ix_journey_steps_step_type", "journey_steps", ["step_type"])
    op.create_index(
        "ix_journey_steps_service_point", "journey_steps", ["service_point"]
    )
    op.create_index("ix_journey_steps_status", "journey_steps", ["status"])
    op.create_index("ix_journey_steps_priority", "journey_steps", ["priority"])
    op.create_index(
        "idx_journey_steps_hospital_status",
        "journey_steps",
        ["hospital_id", "status"],
    )
    op.create_index(
        "idx_journey_steps_queue",
        "journey_steps",
        ["hospital_id", "service_point", "status", "priority"],
    )
    op.create_index(
        "idx_journey_steps_provider",
        "journey_steps",
        ["hospital_id", "provider_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_journey_steps_provider", table_name="journey_steps")
    op.drop_index("idx_journey_steps_queue", table_name="journey_steps")
    op.drop_index("idx_journey_steps_hospital_status", table_name="journey_steps")
    op.drop_index("ix_journey_steps_priority", table_name="journey_steps")
    op.drop_index("ix_journey_steps_status", table_name="journey_steps")
    op.drop_index("ix_journey_steps_service_point", table_name="journey_steps")
    op.drop_index("ix_journey_steps_step_type", table_name="journey_steps")
    op.drop_index("ix_journey_steps_journey_id", table_name="journey_steps")
    op.drop_index("ix_journey_steps_hospital_id", table_name="journey_steps")
    op.drop_table("journey_steps")

    op.drop_index(
        "idx_patient_journeys_hospital_priority", table_name="patient_journeys"
    )
    op.drop_index(
        "idx_patient_journeys_hospital_status", table_name="patient_journeys"
    )
    op.drop_index("idx_patient_journeys_patient", table_name="patient_journeys")
    op.drop_index("ix_patient_journeys_priority", table_name="patient_journeys")
    op.drop_index("ix_patient_journeys_status", table_name="patient_journeys")
    op.drop_index(
        "ix_patient_journeys_journey_number", table_name="patient_journeys"
    )
    op.drop_index("ix_patient_journeys_patient_id", table_name="patient_journeys")
    op.drop_index("ix_patient_journeys_hospital_id", table_name="patient_journeys")
    op.drop_table("patient_journeys")
