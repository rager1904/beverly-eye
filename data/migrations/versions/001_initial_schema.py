"""Initial database schema for UbuntuCare (Zambia).

Revision ID: 001
Revises: None
Create Date: 2026-06-17

Creates all core tables, indexes, foreign keys, constraints,
HNSW vector indexes, pgvector extension, and partitions.
"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Optional[str] = None
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    _create_extensions()
    _create_enums()
    _create_users_tables()
    _create_patient_tables()
    _create_clinical_tables()
    _create_lab_tables()
    _create_pharmacy_tables()
    _create_immunization_tables()
    _create_inventory_tables()
    _create_sync_tables()
    _create_audit_tables()
    _seed_reference_data()
    _create_indexes()
    _create_partitions()


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS sync_queue CASCADE")
    op.execute("DROP TABLE IF EXISTS sync_log CASCADE")
    op.execute("DROP TABLE IF EXISTS inventory_transactions CASCADE")
    op.execute("DROP TABLE IF EXISTS inventory_items CASCADE")
    op.execute("DROP TABLE IF EXISTS immunizations CASCADE")
    op.execute("DROP TABLE IF EXISTS vaccine_stock CASCADE")
    op.execute("DROP TABLE IF EXISTS prescriptions CASCADE")
    op.execute("DROP TABLE IF EXISTS lab_results CASCADE")
    op.execute("DROP TABLE IF EXISTS lab_orders CASCADE")
    op.execute("DROP TABLE IF EXISTS lab_test_catalog CASCADE")
    op.execute("DROP TABLE IF EXISTS clinical_notes CASCADE")
    op.execute("DROP TABLE IF EXISTS vitals CASCADE")
    op.execute("DROP TABLE IF EXISTS visits CASCADE")
    op.execute("DROP TABLE IF EXISTS patient_demographics CASCADE")
    op.execute("DROP TABLE IF EXISTS patients CASCADE")
    op.execute("DROP TABLE IF EXISTS user_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS user_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS role_permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS permissions CASCADE")
    op.execute("DROP TABLE IF EXISTS roles CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS health_facilities CASCADE")
    op.execute("DROP TABLE IF EXISTS districts CASCADE")
    op.execute("DROP TABLE IF EXISTS provinces CASCADE")
    op.execute("DROP TABLE IF EXISTS ai_model_cache CASCADE")
    op.execute("DROP TABLE IF EXISTS knowledge_base CASCADE")
    for enum_name in [
        "user_status", "gender", "visit_type", "visit_status",
        "lab_test_status", "prescription_status", "priority_level",
        "sync_status", "facility_type", "inventory_transaction_type",
        "immunization_status"
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
    op.execute("DROP EXTENSION IF EXISTS vector")


# ── Extensions ──────────────────────────────────────────────────────────────

def _create_extensions() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    # pg_stat_statements requires shared_preload_libraries; skip if not available
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
    except Exception:
        pass


# ── Enums ────────────────────────────────────────────────────────────────────

def _create_enums() -> None:
    op.execute("""
        CREATE TYPE user_status AS ENUM (
            'active', 'inactive', 'suspended', 'pending_verification', 'deleted'
        )
    """)
    op.execute("""
        CREATE TYPE gender AS ENUM (
            'male', 'female', 'other', 'unknown'
        )
    """)
    op.execute("""
        CREATE TYPE visit_type AS ENUM (
            'outpatient', 'inpatient', 'emergency', 'antenatal',
            'postnatal', 'immunization', 'chronic_care', 'review',
            'referral', 'community_health', 'telemedicine'
        )
    """)
    op.execute("""
        CREATE TYPE visit_status AS ENUM (
            'scheduled', 'checked_in', 'in_consultation', 'awaiting_lab',
            'awaiting_pharmacy', 'completed', 'cancelled', 'no_show',
            'referred_out', 'admitted'
        )
    """)
    op.execute("""
        CREATE TYPE lab_test_status AS ENUM (
            'ordered', 'sample_collected', 'sample_received',
            'in_progress', 'completed', 'verified', 'cancelled',
            'rejected'
        )
    """)
    op.execute("""
        CREATE TYPE prescription_status AS ENUM (
            'drafted', 'active', 'dispensed', 'partially_dispensed',
            'cancelled', 'expired', 'completed'
        )
    """)
    op.execute("""
        CREATE TYPE priority_level AS ENUM (
            'critical', 'high', 'medium', 'low'
        )
    """)
    op.execute("""
        CREATE TYPE sync_status AS ENUM (
            'pending', 'syncing', 'synced', 'failed', 'conflict',
            'deferred'
        )
    """)
    op.execute("""
        CREATE TYPE facility_type AS ENUM (
            'tertiary_hospital', 'provincial_hospital', 'district_hospital',
            'general_hospital', 'urban_clinic', 'rural_health_centre',
            'health_post', 'urban_health_centre', 'mini_hospital',
            'specialised_hospital'
        )
    """)
    op.execute("""
        CREATE TYPE inventory_transaction_type AS ENUM (
            'received', 'dispensed', 'transferred_in', 'transferred_out',
            'adjustment_positive', 'adjustment_negative', 'expired',
            'damaged', 'returned', 'count_actual'
        )
    """)
    op.execute("""
        CREATE TYPE immunization_status AS ENUM (
            'scheduled', 'administered', 'overdue', 'refused',
            'contraindicated', 'completed', 'partial'
        )
    """)


# ── Geography Tables ────────────────────────────────────────────────────────

def _create_users_tables() -> None:
    op.create_table(
        "provinces",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("code", sa.String(4), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("capital", sa.String(100), nullable=False),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("area_sq_km", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "districts",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("code", sa.String(8), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("province_id", sa.Integer(),
                  sa.ForeignKey("provinces.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "health_facilities",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("facility_type", sa.String(50), nullable=False),
        sa.Column("district_id", sa.Integer(),
                  sa.ForeignKey("districts.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("province_id", sa.Integer(),
                  sa.ForeignKey("provinces.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(100), nullable=True),
        sa.Column("catchment_population", sa.Integer(), nullable=True),
        sa.Column("has_electricity", sa.Boolean(), default=False),
        sa.Column("has_water", sa.Boolean(), default=False),
        sa.Column("has_internet", sa.Boolean(), default=False),
        sa.Column("has_solar_power", sa.Boolean(), default=False),
        sa.Column("has_cold_chain", sa.Boolean(), default=False),
        sa.Column("has_oxygen_plant", sa.Boolean(), default=False),
        sa.Column("num_beds", sa.Integer(), default=0),
        sa.Column("num_wards", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


# ── Users & Auth ────────────────────────────────────────────────────────────

def _create_patient_tables() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("national_id", sa.String(20), nullable=True, unique=True),
        sa.Column("employee_number", sa.String(50), nullable=True),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"),
                  nullable=True),
        sa.Column("designation", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_verified", sa.Boolean(), default=False),
        sa.Column("must_change_password", sa.Boolean(), default=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(),
                  sa.ForeignKey("roles.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("permission_id", sa.Integer(),
                  sa.ForeignKey("permissions.id", ondelete="CASCADE"),
                  primary_key=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("role_id", sa.Integer(),
                  sa.ForeignKey("roles.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"),
                  nullable=True),
        sa.Column("granted_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_activity_at", sa.DateTime(), nullable=True),
    )


# ── Patient Tables ──────────────────────────────────────────────────────────

def _create_clinical_tables() -> None:
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("nrc_number", sa.String(20), nullable=True, unique=True),
        sa.Column("smartcare_id", sa.String(50), nullable=True, unique=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("other_names", sa.String(100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(20), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("alt_phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address_line1", sa.String(255), nullable=True),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("district_id", sa.Integer(),
                  sa.ForeignKey("districts.id"), nullable=True),
        sa.Column("chiefdom", sa.String(100), nullable=True),
        sa.Column("village", sa.String(100), nullable=True),
        sa.Column("occupation", sa.String(100), nullable=True),
        sa.Column("marital_status", sa.String(20), nullable=True),
        sa.Column("next_of_kin_name", sa.String(200), nullable=True),
        sa.Column("next_of_kin_phone", sa.String(20), nullable=True),
        sa.Column("next_of_kin_relationship", sa.String(50), nullable=True),
        sa.Column("registration_facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=False),
        sa.Column("is_deceased", sa.Boolean(), default=False),
        sa.Column("deceased_at", sa.DateTime(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=False),
        sa.Column("visit_type", sa.String(50), nullable=False),
        sa.Column("visit_status", sa.String(50), nullable=False,
                  server_default="scheduled"),
        sa.Column("priority", sa.String(20), nullable=False,
                  server_default="medium"),
        sa.Column("mode_of_arrival", sa.String(50), nullable=True),
        sa.Column("triage_category", sa.String(20), nullable=True),
        sa.Column("triage_notes", sa.Text(), nullable=True),
        sa.Column("referral_from", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=True),
        sa.Column("referral_to", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=True),
        sa.Column("referral_reason", sa.Text(), nullable=True),
        sa.Column("admitted_at", sa.DateTime(), nullable=True),
        sa.Column("discharged_at", sa.DateTime(), nullable=True),
        sa.Column("discharge_disposition", sa.String(100), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "vitals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("visits.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("temperature_celsius", sa.Float(), nullable=True),
        sa.Column("heart_rate_bpm", sa.Integer(), nullable=True),
        sa.Column("respiratory_rate", sa.Integer(), nullable=True),
        sa.Column("systolic_bp_mmhg", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp_mmhg", sa.Integer(), nullable=True),
        sa.Column("oxygen_saturation_percent", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("bmi", sa.Float(), nullable=True),
        sa.Column("muac_cm", sa.Float(), nullable=True),
        sa.Column("blood_glucose_mmol_l", sa.Float(), nullable=True),
        sa.Column("pain_score", sa.Integer(), nullable=True),
        sa.Column("avpu_score", sa.String(10), nullable=True),
        sa.Column("gcs_score", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(),
                  server_default=sa.func.now()),
    )
    op.create_table(
        "clinical_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("visits.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("note_type", sa.String(50), nullable=False),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("history_of_presenting_illness", sa.Text(), nullable=True),
        sa.Column("past_medical_history", sa.Text(), nullable=True),
        sa.Column("medication_history", sa.Text(), nullable=True),
        sa.Column("family_history", sa.Text(), nullable=True),
        sa.Column("social_history", sa.Text(), nullable=True),
        sa.Column("review_of_systems", sa.Text(), nullable=True),
        sa.Column("physical_examination", sa.Text(), nullable=True),
        sa.Column("assessment", sa.Text(), nullable=False),
        sa.Column("diagnosis_icd10_codes", postgresql.ARRAY(sa.String(10)),
                  nullable=True),
        sa.Column("diagnosis_text", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.Column("is_confirmed_diagnosis", sa.Boolean(), default=False),
        sa.Column("icd10_embeddings", postgresql.ARRAY(sa.Float()),
                  nullable=True),
        sa.Column("clinical_note_embedding", postgresql.ARRAY(sa.Float()),
                  nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("is_signed_off", sa.Boolean(), default=False),
        sa.Column("signed_off_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("signed_off_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


# ── Lab Tables ──────────────────────────────────────────────────────────────

def _create_lab_tables() -> None:
    op.create_table(
        "lab_test_catalog",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("specimen_type", sa.String(100), nullable=True),
        sa.Column("method", sa.String(200), nullable=True),
        sa.Column("turnaround_time_minutes", sa.Integer(), nullable=True),
        sa.Column("requires_cold_chain", sa.Boolean(), default=False),
        sa.Column("is_rapid_test", sa.Boolean(), default=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "lab_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_number", sa.String(50), nullable=False, unique=True),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("visits.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("test_id", sa.Integer(),
                  sa.ForeignKey("lab_test_catalog.id"), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False,
                  server_default="medium"),
        sa.Column("status", sa.String(50), nullable=False,
                  server_default="ordered"),
        sa.Column("ordered_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ordered_at", sa.DateTime(),
                  server_default=sa.func.now()),
        sa.Column("sample_collected_at", sa.DateTime(), nullable=True),
        sa.Column("sample_collected_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sample_received_at", sa.DateTime(), nullable=True),
        sa.Column("sample_received_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("specimen_id", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "lab_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("lab_order_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("lab_orders.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("result_value", sa.Text(), nullable=True),
        sa.Column("result_numeric", sa.Float(), nullable=True),
        sa.Column("result_unit", sa.String(50), nullable=True),
        sa.Column("reference_range_low", sa.Float(), nullable=True),
        sa.Column("reference_range_high", sa.Float(), nullable=True),
        sa.Column("is_abnormal", sa.Boolean(), default=False),
        sa.Column("is_positive", sa.Boolean(), nullable=True),
        sa.Column("result_text", sa.Text(), nullable=True),
        sa.Column("interpretation", sa.Text(), nullable=True),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("performed_at", sa.DateTime(), nullable=False),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


# ── Pharmacy Tables ─────────────────────────────────────────────────────────

def _create_pharmacy_tables() -> None:
    op.create_table(
        "prescriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("prescription_number", sa.String(50), nullable=False,
                  unique=True),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("visits.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("medicine_code", sa.String(20), nullable=False),
        sa.Column("medicine_name", sa.String(200), nullable=False),
        sa.Column("dosage", sa.String(100), nullable=False),
        sa.Column("frequency", sa.String(100), nullable=False),
        sa.Column("route", sa.String(50), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("quantity_unit", sa.String(20), nullable=False),
        sa.Column("dispensed_quantity", sa.Float(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False,
                  server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_controlled_drug", sa.Boolean(), default=False),
        sa.Column("prescribed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("dispensed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("dispensed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


# ── Immunization Tables ─────────────────────────────────────────────────────

def _create_immunization_tables() -> None:
    op.create_table(
        "immunizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("vaccine_code", sa.String(20), nullable=False),
        sa.Column("vaccine_name", sa.String(200), nullable=False),
        sa.Column("dose_number", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("administered_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False,
                  server_default="scheduled"),
        sa.Column("batch_number", sa.String(50), nullable=True),
        sa.Column("manufacturer", sa.String(100), nullable=True),
        sa.Column("administration_site", sa.String(50), nullable=True),
        sa.Column("route", sa.String(50), nullable=True),
        sa.Column("lot_number", sa.String(50), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("adverse_event", sa.Text(), nullable=True),
        sa.Column("contraindication_reason", sa.Text(), nullable=True),
        sa.Column("administered_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "vaccine_stock",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("vaccine_code", sa.String(20), nullable=False),
        sa.Column("batch_number", sa.String(50), nullable=False),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=False),
        sa.Column("quantity_received", sa.Integer(), default=0),
        sa.Column("quantity_dispensed", sa.Integer(), default=0),
        sa.Column("quantity_wasted", sa.Integer(), default=0),
        sa.Column("quantity_available", sa.Integer(), default=0),
        sa.Column("manufacturer", sa.String(100), nullable=True),
        sa.Column("manufacture_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("requires_cold_chain", sa.Boolean(), default=True),
        sa.Column("storage_temperature_celsius", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


# ── Inventory Tables ────────────────────────────────────────────────────────

def _create_inventory_tables() -> None:
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("item_code", sa.String(20), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=False),
        sa.Column("current_stock", sa.Float(), default=0),
        sa.Column("minimum_stock", sa.Float(), default=0),
        sa.Column("maximum_stock", sa.Float(), nullable=True),
        sa.Column("reorder_point", sa.Float(), default=0),
        sa.Column("unit_of_measure", sa.String(50), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("batch_number", sa.String(50), nullable=True),
        sa.Column("manufacturer", sa.String(100), nullable=True),
        sa.Column("storage_conditions", sa.String(200), nullable=True),
        sa.Column("is_controlled", sa.Boolean(), default=False),
        sa.Column("is_refrigerated", sa.Boolean(), default=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("item_id", sa.Integer(),
                  sa.ForeignKey("inventory_items.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("quantity_before", sa.Float(), nullable=False),
        sa.Column("quantity_after", sa.Float(), nullable=False),
        sa.Column("reference_number", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


# ── Sync Tables ─────────────────────────────────────────────────────────────

def _create_sync_tables() -> None:
    op.create_table(
        "sync_queue",
        sa.Column("id", sa.BigInteger(), autoincrement=True,
                  primary_key=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", sa.String(100), nullable=False),
        sa.Column("operation", sa.String(10), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False,
                  server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="pending"),
        sa.Column("retry_count", sa.Integer(), default=0),
        sa.Column("max_retries", sa.Integer(), default=5),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(),
                  server_default=sa.func.now()),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "sync_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True,
                  primary_key=True),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=True),
        sa.Column("sync_type", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("records_synced", sa.Integer(), default=0),
        sa.Column("bytes_uploaded", sa.BigInteger(), default=0),
        sa.Column("bytes_downloaded", sa.BigInteger(), default=0),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )


# ── Audit Tables ────────────────────────────────────────────────────────────

def _create_audit_tables() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True,
                  primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("facility_id", sa.Integer(),
                  sa.ForeignKey("health_facilities.id"), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(),
                  server_default=sa.func.now()),
    )


# ── Knowledge Base ──────────────────────────────────────────────────────────

def _seed_reference_data() -> None:
    op.create_table(
        "knowledge_base",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("language", sa.String(10), nullable=False,
                  server_default="en"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_embedding", postgresql.ARRAY(sa.Float()),
                  nullable=True),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("version", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "ai_model_cache",
        sa.Column("id", sa.BigInteger(), autoincrement=True,
                  primary_key=True),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("input_data", postgresql.JSONB(), nullable=False),
        sa.Column("output_data", postgresql.JSONB(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(),
                  server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )


# ── Indexes ──────────────────────────────────────────────────────────────────

def _create_indexes() -> None:
    # Patients
    op.create_index("idx_patients_nrc", "patients", ["nrc_number"])
    op.create_index("idx_patients_name", "patients",
                    ["last_name", "first_name"])
    op.create_index("idx_patients_dob", "patients", ["date_of_birth"])
    op.create_index("idx_patients_gender", "patients", ["gender"])
    op.create_index("idx_patients_phone", "patients", ["phone"])
    op.create_index("idx_patients_facility", "patients",
                    ["registration_facility_id"])
    op.create_index("idx_patients_created", "patients", ["created_at"])

    # Visits
    op.create_index("idx_visits_patient", "visits", ["patient_id"])
    op.create_index("idx_visits_facility", "visits", ["facility_id"])
    op.create_index("idx_visits_status", "visits", ["visit_status"])
    op.create_index("idx_visits_type", "visits", ["visit_type"])
    op.create_index("idx_visits_created", "visits", ["created_at"])
    op.create_index("idx_visits_facility_status", "visits",
                    ["facility_id", "visit_status"])
    op.create_index("idx_visits_patient_created", "visits",
                    ["patient_id", "created_at"])

    # Clinical Notes
    op.create_index("idx_notes_visit", "clinical_notes", ["visit_id"])
    op.create_index("idx_notes_patient", "clinical_notes", ["patient_id"])
    op.create_index("idx_notes_signed", "clinical_notes", ["is_signed_off"])
    op.create_index("idx_notes_lookup", "clinical_notes",
                    ["patient_id", "created_at"])

    # Lab
    op.create_index("idx_lab_orders_visit", "lab_orders", ["visit_id"])
    op.create_index("idx_lab_orders_patient", "lab_orders", ["patient_id"])
    op.create_index("idx_lab_orders_status", "lab_orders", ["status"])
    op.create_index("idx_lab_orders_number", "lab_orders", ["order_number"])
    op.create_index("idx_lab_results_order", "lab_results", ["lab_order_id"])
    op.create_index("idx_lab_results_patient", "lab_results", ["patient_id"])
    op.create_index("idx_lab_results_performed", "lab_results",
                    ["performed_at"])

    # Prescriptions
    op.create_index("idx_rx_visit", "prescriptions", ["visit_id"])
    op.create_index("idx_rx_patient", "prescriptions", ["patient_id"])
    op.create_index("idx_rx_status", "prescriptions", ["status"])
    op.create_index("idx_rx_medicine", "prescriptions", ["medicine_code"])

    # Immunizations
    op.create_index("idx_immunizations_patient", "immunizations",
                    ["patient_id"])
    op.create_index("idx_immunizations_vaccine", "immunizations",
                    ["vaccine_code"])
    op.create_index("idx_immunizations_status", "immunizations", ["status"])
    op.create_index("idx_immunizations_due", "immunizations",
                    ["scheduled_date", "status"])
    op.create_index("idx_vaccine_stock_facility", "vaccine_stock",
                    ["facility_id", "vaccine_code"])

    # Inventory
    op.create_index("idx_inventory_facility", "inventory_items",
                    ["facility_id"])
    op.create_index("idx_inventory_code", "inventory_items", ["item_code"])
    op.create_index("idx_inventory_stock_level", "inventory_items",
                    ["facility_id", "current_stock"])
    op.create_index("idx_inventory_transactions_item",
                    "inventory_transactions", ["item_id"])
    op.create_index("idx_inventory_transactions_facility",
                    "inventory_transactions", ["facility_id"])
    op.create_index("idx_inventory_transactions_type",
                    "inventory_transactions", ["transaction_type"])

    # Sync
    op.create_index("idx_sync_queue_status", "sync_queue",
                    ["status", "priority"])
    op.create_index("idx_sync_queue_device", "sync_queue", ["device_id"])
    op.create_index("idx_sync_queue_created", "sync_queue", ["created_at"])
    op.create_index("idx_sync_log_device", "sync_log", ["device_id"])
    op.create_index("idx_sync_log_started", "sync_log", ["started_at"])

    # Audit
    op.create_index("idx_audit_user", "audit_log", ["user_id"])
    op.create_index("idx_audit_action", "audit_log", ["action"])
    op.create_index("idx_audit_resource", "audit_log",
                    ["resource_type", "resource_id"])
    op.create_index("idx_audit_patient", "audit_log", ["patient_id"])
    op.create_index("idx_audit_created", "audit_log", ["created_at"])

    # Knowledge Base
    op.create_index("idx_kb_category", "knowledge_base", ["category"])
    op.create_index("idx_kb_language", "knowledge_base", ["language"])

    # Users
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_facility", "users", ["facility_id"])
    op.create_index("idx_user_sessions_user", "user_sessions", ["user_id"])
    op.create_index("idx_user_sessions_active", "user_sessions",
                    ["user_id", "is_active"])

    # AI Model Cache
    op.create_index("idx_ai_cache_model", "ai_model_cache", ["model_name"])
    op.create_index("idx_ai_cache_hash", "ai_model_cache",
                    ["model_name", "input_hash"])
    op.create_index("idx_ai_cache_expires", "ai_model_cache", ["expires_at"])

    # Vitals
    op.create_index("idx_vitals_visit", "vitals", ["visit_id"])
    op.create_index("idx_vitals_patient", "vitals", ["patient_id"])

    # Full-text search indexes (PostgreSQL)
    op.execute("""
        CREATE INDEX idx_patients_fts ON patients
        USING GIN (
            to_tsvector('english', coalesce(first_name, '') || ' ' ||
                        coalesce(last_name, '') || ' ' ||
                        coalesce(other_names, ''))
        )
    """)
    op.execute("""
        CREATE INDEX idx_clinical_notes_fts ON clinical_notes
        USING GIN (to_tsvector('english', coalesce(assessment, '') || ' ' ||
                    coalesce(diagnosis_text, '')))
    """)

    # Vector indexes disabled - use Qdrant for vector search


# ── Partitions ──────────────────────────────────────────────────────────────

def _create_partitions() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS patients_partitioned (
            LIKE patients INCLUDING DEFAULTS INCLUDING CONSTRAINTS,
            PRIMARY KEY (id, registration_facility_id)
        ) PARTITION BY LIST (registration_facility_id)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log_partitioned (
            LIKE audit_log INCLUDING DEFAULTS INCLUDING CONSTRAINTS,
            PRIMARY KEY (id, facility_id)
        ) PARTITION BY LIST (facility_id)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS sync_queue_partitioned (
            LIKE sync_queue INCLUDING DEFAULTS INCLUDING CONSTRAINTS,
            PRIMARY KEY (id, facility_id)
        ) PARTITION BY LIST (facility_id)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS clinical_notes_partitioned (
            LIKE clinical_notes INCLUDING DEFAULTS INCLUDING CONSTRAINTS,
            PRIMARY KEY (id, visit_id)
        ) PARTITION BY LIST (visit_id)
    """)
