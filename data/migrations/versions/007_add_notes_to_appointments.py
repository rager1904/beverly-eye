"""Add missing columns to appointments table (notes, location, encounter_id, etc.).

Revision ID: 007
Revises: 006
Create Date: 2026-07-04
"""

from typing import Optional, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "007"
down_revision: Optional[str] = "006"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # Older installations created these columns outside Alembic. Preserve them
    # while recording this revision and adding anything genuinely missing.
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("appointments")}
    columns = [
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("encounter_id", UUID(as_uuid=True), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("language_preference", sa.String(10), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
        sa.Column("hospital_id", UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("'00000000-0000-0000-0000-000000000000'")),
    ]
    for column in columns:
        if column.name not in existing:
            op.add_column("appointments", column)


def downgrade() -> None:
    op.drop_column("appointments", "hospital_id")
    op.drop_column("appointments", "updated_by")
    op.drop_column("appointments", "created_by")
    op.drop_column("appointments", "language_preference")
    op.drop_column("appointments", "cancel_reason")
    op.drop_column("appointments", "cancelled_at")
    op.drop_column("appointments", "checked_in_at")
    op.drop_column("appointments", "encounter_id")
    op.drop_column("appointments", "location")
    op.drop_column("appointments", "notes")
