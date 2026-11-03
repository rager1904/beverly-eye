"""Add specimen tracking and verification to EMR lab orders.

Revision ID: 008
Revises: 007
Create Date: 2026-10-29
"""

from typing import Optional, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "008"
down_revision: Optional[str] = "007"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def _audit_columns():
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
    ]


def _ensure_emr_order_baseline():
    """Freeze the pre-008 EMR schema omitted from the original migration chain.

    Legacy lab_orders/lab_results are different tables and remain untouched.
    Do not import live ORM metadata: future model changes must not rewrite history.
    """
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    definitions = {
        "encountertype": ("outpatient", "inpatient", "emergency", "telemedicine", "home_visit", "consultation", "follow_up"),
        "encounterstatus": ("planned", "in_progress", "on_hold", "completed", "cancelled", "discharged"),
        "ordertype": ("lab", "imaging", "referral", "procedure", "blood_bank"),
        "orderpriority": ("routine", "urgent", "stat"),
        "orderstatus": ("draft", "ordered", "in_progress", "completed", "cancelled", "resulted"),
        "resultinterpretation": ("normal", "abnormal", "critical", "pending", "not_interpreted"),
    }
    for name, labels in definitions.items():
        postgresql.ENUM(*labels, name=name).create(bind, checkfirst=True)

    def enum_type(name):
        return postgresql.ENUM(*definitions[name], name=name, create_type=False)

    def identifier():
        return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))

    def patient():
        return sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False)

    if "encounters" not in tables:
        op.create_table(
            "encounters", identifier(), patient(),
            sa.Column("encounter_type", enum_type("encountertype"), nullable=False),
            sa.Column("encounter_datetime", sa.DateTime(), nullable=False),
            sa.Column("status", enum_type("encounterstatus"), nullable=False, server_default="planned"),
            sa.Column("chief_complaint", sa.Text()), sa.Column("triage_notes", sa.Text()),
            sa.Column("department", sa.String(100)), sa.Column("facility_id", sa.String(50)),
            *[sa.Column(name, sa.Integer()) for name in ("blood_pressure_systolic", "blood_pressure_diastolic", "heart_rate", "respiratory_rate", "pain_score")],
            *[sa.Column(name, sa.Numeric(5, 2)) for name in ("temperature", "oxygen_saturation", "bmi")],
            sa.Column("weight", sa.Numeric(6, 2)), sa.Column("height", sa.Numeric(6, 2)),
            sa.Column("provider_id", sa.String(50)), sa.Column("provider_name", sa.String(200)),
            *_audit_columns(),
        )
        op.create_index("idx_encounters_patient", "encounters", ["patient_id", "encounter_datetime"])
        op.create_index("idx_encounters_hospital_status", "encounters", ["hospital_id", "status"])
    if "orders" not in tables:
        op.create_table(
            "orders", identifier(), patient(),
            sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id")),
            sa.Column("order_type", enum_type("ordertype"), nullable=False),
            sa.Column("order_code", sa.String(50), nullable=False),
            sa.Column("order_description", sa.String(500), nullable=False),
            sa.Column("priority", enum_type("orderpriority"), nullable=False, server_default="routine"),
            sa.Column("status", enum_type("orderstatus"), nullable=False, server_default="draft"),
            sa.Column("ordered_by", sa.String(200)), sa.Column("ordered_datetime", sa.DateTime()),
            sa.Column("performed_by", sa.String(200)), sa.Column("performed_datetime", sa.DateTime()),
            sa.Column("result_id", postgresql.UUID(as_uuid=True)),
            sa.Column("clinical_notes", sa.Text()), sa.Column("instructions", sa.Text()),
            sa.Column("diagnosis_id", postgresql.UUID(as_uuid=True)), *_audit_columns(),
        )
        op.create_index("idx_orders_status", "orders", ["status", "hospital_id"])
        op.create_index("ix_orders_patient_id", "orders", ["patient_id"])
    if "results" not in tables:
        op.create_table(
            "results", identifier(), patient(),
            sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("result_type", sa.String(50), nullable=False),
            sa.Column("result_code", sa.String(50), nullable=False),
            sa.Column("result_description", sa.String(500), nullable=False),
            sa.Column("result_value", sa.Text()), sa.Column("result_unit", sa.String(50)),
            sa.Column("reference_range_low", sa.String(50)), sa.Column("reference_range_high", sa.String(50)),
            sa.Column("interpretation", enum_type("resultinterpretation"), nullable=False, server_default="pending"),
            sa.Column("performed_by", sa.String(200)), sa.Column("performed_datetime", sa.DateTime()),
            sa.Column("result_datetime", sa.DateTime()), sa.Column("attachments", sa.Text()),
            sa.Column("notes", sa.Text()), *_audit_columns(),
        )
        op.create_index("ix_results_patient_id", "results", ["patient_id"])


def upgrade() -> None:
    _ensure_emr_order_baseline()
    # No new labels are used within this migration; they become usable on commit.
    for value in ("collected", "received", "verified"):
        op.execute(sa.text(f"ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS '{value}'"))

    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("orders")}
    columns = [
        sa.Column("specimen_type", sa.String(100)), sa.Column("specimen_id", sa.String(100)),
        sa.Column("collected_by", sa.String(200)), sa.Column("collected_datetime", sa.DateTime()),
        sa.Column("received_by", sa.String(200)), sa.Column("received_datetime", sa.DateTime()),
        sa.Column("verified_by", sa.String(200)), sa.Column("verified_datetime", sa.DateTime()),
    ]
    for column in columns:
        if column.name not in existing:
            op.add_column("orders", column)
    if "idx_orders_specimen_id" not in {index["name"] for index in inspector.get_indexes("orders")}:
        op.create_index("idx_orders_specimen_id", "orders", ["hospital_id", "specimen_id"])
    if "uq_orders_hospital_specimen" not in {constraint["name"] for constraint in inspector.get_unique_constraints("orders")}:
        op.create_unique_constraint("uq_orders_hospital_specimen", "orders", ["hospital_id", "specimen_id"])
    result_columns = {column["name"] for column in inspector.get_columns("results")}
    for column in (sa.Column("verified_by", sa.String(200)), sa.Column("verified_datetime", sa.DateTime())):
        if column.name not in result_columns:
            op.add_column("results", column)


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
    # Preserve baseline encounters/orders/results and all their pre-008 data.
    # PostgreSQL cannot safely remove enum labels while dependent rows/types exist.
