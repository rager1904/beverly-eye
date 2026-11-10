"""Align the clinical note table with EMR while preserving legacy note authors.

Revision ID: 016
Revises: 015
"""

import sqlalchemy as sa
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade():
    columns = [
        sa.Column("encounter_id", sa.Uuid(), sa.ForeignKey("encounters.id")),
        sa.Column("hospital_id", sa.Uuid()),
        sa.Column("title", sa.String(500)),
        sa.Column("subjective", sa.Text()),
        sa.Column("objective", sa.Text()),
        sa.Column("procedure_code", sa.String(20)),
        sa.Column("procedure_description", sa.String(500)),
        sa.Column("authored_by", sa.String(200)),
        sa.Column("authored_datetime", sa.DateTime()),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_confidential", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("emr_created_by", sa.String(200)),
        sa.Column("updated_by", sa.String(200)),
    ]
    for column in columns:
        op.add_column("clinical_notes", column)
    # Legacy visits and local user IDs are not required for standalone EMR notes.
    for name in ("visit_id", "created_by", "assessment"):
        op.alter_column("clinical_notes", name, nullable=True)
    op.create_index("ix_clinical_notes_hospital_id", "clinical_notes", ["hospital_id"])


def downgrade():
    raise RuntimeError("Downgrading would discard clinical notes. Restore from a reviewed backup.")
