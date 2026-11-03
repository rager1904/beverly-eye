"""Add specimen tracking and verification to EMR lab orders.

Revision ID: 008
Revises: 007
Create Date: 2026-10-29
"""

from typing import Optional, Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "008"
down_revision: Optional[str] = "007"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # PostgreSQL enum values must exist before rows can enter the new workflow states.
    for value in ("collected", "received", "verified"):
        op.execute(
            sa.text(
                f"ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS '{value}'"
            )
        )

    op.add_column("orders", sa.Column("specimen_type", sa.String(100), nullable=True))
    op.add_column("orders", sa.Column("specimen_id", sa.String(100), nullable=True))
    op.add_column("orders", sa.Column("collected_by", sa.String(200), nullable=True))
    op.add_column("orders", sa.Column("collected_datetime", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("received_by", sa.String(200), nullable=True))
    op.add_column("orders", sa.Column("received_datetime", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("verified_by", sa.String(200), nullable=True))
    op.add_column("orders", sa.Column("verified_datetime", sa.DateTime(), nullable=True))
    op.create_index("idx_orders_specimen_id", "orders", ["hospital_id", "specimen_id"])
    op.create_unique_constraint(
        "uq_orders_hospital_specimen", "orders", ["hospital_id", "specimen_id"]
    )

    op.add_column("results", sa.Column("verified_by", sa.String(200), nullable=True))
    op.add_column("results", sa.Column("verified_datetime", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("results", "verified_datetime")
    op.drop_column("results", "verified_by")
    op.drop_constraint("uq_orders_hospital_specimen", "orders", type_="unique")
    op.drop_index("idx_orders_specimen_id", table_name="orders")
    op.drop_column("orders", "verified_datetime")
    op.drop_column("orders", "verified_by")
    op.drop_column("orders", "received_datetime")
    op.drop_column("orders", "received_by")
    op.drop_column("orders", "collected_datetime")
    op.drop_column("orders", "collected_by")
    op.drop_column("orders", "specimen_id")
    op.drop_column("orders", "specimen_type")
    # PostgreSQL cannot safely remove enum labels while dependent rows/types exist.
