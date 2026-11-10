"""Store pharmacy stock separately from patient medication orders.

Revision ID: 015
Revises: 014
"""

import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pharmacy_stock",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("hospital_id", sa.Uuid(), sa.ForeignKey("hospitals.id"), nullable=False),
        sa.Column("medication_name", sa.String(200), nullable=False),
        sa.Column("generic_name", sa.String(200)),
        sa.Column("category", sa.String(100)),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("reorder_level", sa.Integer()),
        sa.Column("expiry_date", sa.Date()),
        sa.Column("supplier", sa.String(200)),
        sa.Column("cost_price", sa.Numeric(12, 2)),
        sa.Column("selling_price", sa.Numeric(12, 2)),
        sa.Column("batch_number", sa.String(100)),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_pharmacy_stock_quantity"),
    )
    op.create_index("ix_pharmacy_stock_hospital_name", "pharmacy_stock", ["hospital_id", "medication_name"])


def downgrade():
    op.drop_table("pharmacy_stock")
