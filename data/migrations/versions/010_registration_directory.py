"""Add registration billing fields and hospital directory tables.

Revision ID: 010
Revises: 009
Create Date: 2026-10-31

The hospital-management ORM models (hospitals, departments, staff) were never
part of the Alembic chain, so a fresh deployment could not route patients to a
department or doctor. This migration adds those tables when they are missing
and records the per-visit billing details captured at registration.
"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "010"
down_revision: Optional[str] = "009"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None

DEFAULT_HOSPITAL_ID = "00000000-0000-4000-8000-000000000001"


def _inspector():
    context = op.get_context()
    if getattr(context, "as_sql", False):
        # Offline --sql mode: no live database to inspect.
        return None
    bind = op.get_bind()
    if bind is None:
        return None
    return sa.inspect(bind)


def _has_table(inspector, table_name: str) -> bool:
    if inspector is None:
        # Offline preview assumes migration 009 already created journeys.
        return table_name == "patient_journeys"
    return inspector.has_table(table_name)


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if inspector is None or not inspector.has_table(table_name):
        return False
    return any(
        column["name"] == column_name
        for column in inspector.get_columns(table_name)
    )


def _create_hospitals(inspector) -> None:
    if _has_table(inspector, "hospitals"):
        return
    op.create_table(
        "hospitals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        # Enum values are persisted by SQLAlchemy using the Python member
        # names, so a plain string column keeps the ORM compatible.
        sa.Column(
            "level", sa.String(40), nullable=False, server_default="tertiary_hospital"
        ),
        sa.Column("address_line", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("province", sa.String(100), nullable=False, server_default="Lusaka"),
        sa.Column("district", sa.String(100), nullable=False, server_default="Lusaka"),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("website", sa.String(200), nullable=True),
        sa.Column("bed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
    )
    op.create_index("ix_hospitals_code", "hospitals", ["code"], unique=True)


def _create_departments(inspector) -> None:
    if _has_table(inspector, "departments"):
        return
    op.create_table(
        "departments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(20), nullable=True),
        sa.Column("head_of_department", sa.String(200), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("phone_extension", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "hospital_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hospitals.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
    )
    op.create_index(
        "ix_departments_hospital_id", "departments", ["hospital_id"]
    )


def _create_staff(inspector) -> None:
    if _has_table(inspector, "staff"):
        return
    op.create_table(
        "staff",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.String(50), nullable=True, unique=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(40), nullable=False, server_default="doctor"),
        sa.Column("speciality", sa.String(200), nullable=True),
        sa.Column(
            "department_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("departments.id"),
            nullable=True,
        ),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("license_number", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "max_hours_per_week", sa.Integer(), nullable=False, server_default="40"
        ),
        sa.Column(
            "hospital_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hospitals.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_by", sa.String(200), nullable=True),
    )
    op.create_index("ix_staff_hospital_id", "staff", ["hospital_id"])
    op.create_index("ix_staff_department_id", "staff", ["department_id"])


def _seed_default_hospital() -> None:
    op.execute(
        sa.text(
            f"""
            INSERT INTO hospitals (
                id, name, code, level, address_line, city, province, district,
                phone, bed_count, is_active
            )
            VALUES (
                '{DEFAULT_HOSPITAL_ID}'::uuid,
                'University Teaching Hospital', 'UTH001',
                'tertiary_hospital', 'Off Great East Road', 'Lusaka',
                'Lusaka', 'Lusaka', '+260211250000', 1500, TRUE
            )
            ON CONFLICT (id) DO NOTHING
            """
        )
    )


def upgrade() -> None:
    inspector = _inspector()

    # Per-visit billing / registration details.
    if _has_table(inspector, "patient_journeys"):
        if not _has_column(inspector, "patient_journeys", "payment_scheme"):
            op.add_column(
                "patient_journeys",
                sa.Column(
                    "payment_scheme",
                    sa.String(50),
                    nullable=False,
                    server_default="cash",
                ),
            )
            op.create_index(
                "ix_patient_journeys_payment_scheme",
                "patient_journeys",
                ["payment_scheme"],
            )
        if not _has_column(inspector, "patient_journeys", "visit_type"):
            op.add_column(
                "patient_journeys",
                sa.Column(
                    "visit_type",
                    sa.String(20),
                    nullable=False,
                    server_default="new",
                ),
            )
            op.create_index(
                "ix_patient_journeys_visit_type",
                "patient_journeys",
                ["visit_type"],
            )
        if not _has_column(inspector, "patient_journeys", "payment_status"):
            op.add_column(
                "patient_journeys",
                sa.Column(
                    "payment_status",
                    sa.String(20),
                    nullable=False,
                    server_default="unpaid",
                ),
            )
            op.create_index(
                "ix_patient_journeys_payment_status",
                "patient_journeys",
                ["payment_status"],
            )
        if not _has_column(inspector, "patient_journeys", "scheme_number"):
            op.add_column(
                "patient_journeys",
                sa.Column("scheme_number", sa.String(80), nullable=True),
            )

    # Directory used by registration routing and admin management.
    _create_hospitals(inspector)
    _create_departments(inspector)
    _create_staff(inspector)
    _seed_default_hospital()


def downgrade() -> None:
    inspector = _inspector()

    if _has_table(inspector, "staff"):
        op.drop_table("staff")
    if _has_table(inspector, "departments"):
        op.drop_table("departments")
    if _has_table(inspector, "hospitals"):
        op.drop_table("hospitals")

    if _has_table(inspector, "patient_journeys"):
        if _has_column(inspector, "patient_journeys", "scheme_number"):
            op.drop_column("patient_journeys", "scheme_number")
        if _has_column(inspector, "patient_journeys", "payment_status"):
            op.drop_index(
                "ix_patient_journeys_payment_status", table_name="patient_journeys"
            )
            op.drop_column("patient_journeys", "payment_status")
        if _has_column(inspector, "patient_journeys", "visit_type"):
            op.drop_index(
                "ix_patient_journeys_visit_type", table_name="patient_journeys"
            )
            op.drop_column("patient_journeys", "visit_type")
        if _has_column(inspector, "patient_journeys", "payment_scheme"):
            op.drop_index(
                "ix_patient_journeys_payment_scheme", table_name="patient_journeys"
            )
            op.drop_column("patient_journeys", "payment_scheme")
