"""Add EMR patient fields to the legacy patient table without assigning tenants.

Revision ID: 014
Revises: 013
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade():
    columns = [
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True)),
        sa.Column("middle_name", sa.String(100)),
        sa.Column("address_line", sa.String(500)),
        sa.Column("city", sa.String(100)),
        sa.Column("province", sa.String(100)),
        sa.Column("district", sa.String(100)),
        sa.Column("nationality", sa.String(100)),
        sa.Column("emergency_contact_name", sa.String(200)),
        sa.Column("emergency_contact_phone", sa.String(20)),
        sa.Column("emergency_contact_relation", sa.String(100)),
        sa.Column("insurance_provider", sa.String(200)),
        sa.Column("insurance_number", sa.String(50)),
        sa.Column("insurance_expiry", sa.Date()),
        sa.Column("nhima_member", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("nhima_number", sa.String(50)),
        sa.Column("photo_url", sa.String(500)),
        sa.Column("language_preference", sa.String(50)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.String(200)),
        sa.Column("updated_by", sa.String(200)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("deleted_by", sa.String(200)),
    ]
    context = op.get_context()
    existing = (
        {col["name"] for col in sa.inspect(op.get_bind()).get_columns("patients")}
        if not context.as_sql else set()
    )
    for column in columns:
        if column.name not in existing:
            op.add_column("patients", column)
    if "registration_facility_id" in existing or context.as_sql:
        # EMR uses a hospital UUID; the legacy registry uses integer facility IDs.
        op.alter_column("patients", "registration_facility_id", nullable=True)
    op.execute("CREATE INDEX IF NOT EXISTS ix_patients_hospital_id ON patients (hospital_id)")


def downgrade():
    raise RuntimeError("Downgrading would discard patient data; restore from a reviewed backup.")
