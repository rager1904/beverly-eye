"""Seed RBAC data: roles, permissions, default users.

Revision ID: 004
Revises: 003
Create Date: 2026-06-17
"""

from typing import Optional, Sequence
from uuid import uuid4
import os

from alembic import op
from sqlalchemy import text

revision: str = "004"
down_revision: Optional[str] = "003"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def _demo_seed_enabled() -> bool:
    """Demo accounts are opt-in in production and opt-out in development."""
    explicit = os.getenv("UBUNTUCARE_SEED_DEMO_DATA")
    if explicit is not None:
        return explicit.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("ENVIRONMENT", "production").strip().lower() != "production"


def upgrade() -> None:
    _seed_permissions()
    _seed_roles()
    _seed_role_permissions()
    if _demo_seed_enabled():
        _seed_default_users()


def downgrade() -> None:
    op.execute("DELETE FROM user_sessions")
    op.execute("DELETE FROM user_roles")
    op.execute("DELETE FROM users WHERE username IN ('admin', 'uth_admin', 'moh_officer', 'dr_mwamba', 'nurse_banda')")
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM permissions")
    op.execute("DELETE FROM roles")


def _seed_permissions() -> None:
    permissions = [
        # Patient
        ("patient:read", "View patient demographics", "patient", "read"),
        ("patient:create", "Register new patients", "patient", "create"),
        ("patient:update", "Update patient records", "patient", "update"),
        ("patient:delete", "Delete patient records", "patient", "delete"),
        ("patient:search", "Search across patients", "patient", "search"),
        ("patient:merge", "Merge duplicate patient records", "patient", "merge"),
        ("patient:export", "Export patient data", "patient", "export"),

        # Clinical
        ("clinical:read", "View clinical notes", "clinical", "read"),
        ("clinical:write", "Create/edit clinical notes", "clinical", "write"),
        ("clinical:sign", "Sign off clinical notes", "clinical", "sign"),
        ("clinical:diagnosis", "Add/modify diagnoses", "clinical", "diagnosis"),
        ("clinical:delete_note", "Delete clinical notes", "clinical", "delete_note"),
        ("clinical:read_all", "View all clinical notes (any provider)", "clinical", "read_all"),

        # Consultation
        ("consult:perform", "Perform consultations", "consult", "perform"),
        ("consult:triage", "Perform triage", "consult", "triage"),
        ("consult:refer", "Refer patients to other facilities", "consult", "refer"),
        ("consult:admit", "Admit patients", "consult", "admit"),
        ("consult:discharge", "Discharge patients", "consult", "discharge"),

        # Lab
        ("lab:order", "Order lab tests", "lab", "order"),
        ("lab:read", "View lab results", "lab", "read"),
        ("lab:perform", "Perform tests/enter results", "lab", "perform"),
        ("lab:verify", "Verify/publish lab results", "lab", "verify"),
        ("lab:manage_catalog", "Manage lab test catalog", "lab", "manage_catalog"),
        ("lab:read_all", "View all lab results", "lab", "read_all"),

        # Pharmacy
        ("pharmacy:prescribe", "Write prescriptions", "pharmacy", "prescribe"),
        ("pharmacy:dispense", "Dispense medication", "pharmacy", "dispense"),
        ("pharmacy:read", "View prescriptions", "pharmacy", "read"),
        ("pharmacy:manage_stock", "Manage inventory", "pharmacy", "manage_stock"),
        ("pharmacy:adjust_stock", "Stock adjustments", "pharmacy", "adjust_stock"),
        ("pharmacy:controlled_drugs", "Access controlled drugs", "pharmacy", "controlled_drugs"),
        ("pharmacy:verify", "Verify dispensation", "pharmacy", "verify"),
        ("pharmacy:read_all", "View all prescriptions", "pharmacy", "read_all"),

        # Immunization
        ("immunization:administer", "Administer vaccines", "immunization", "administer"),
        ("immunization:read", "View immunization records", "immunization", "read"),
        ("immunization:schedule", "Schedule immunizations", "immunization", "schedule"),
        ("immunization:manage_stock", "Manage vaccine stock", "immunization", "manage_stock"),
        ("immunization:report", "Generate EPI reports", "immunization", "report"),

        # Maternity
        ("maternity:anc", "Manage ANC records", "maternity", "anc"),
        ("maternity:delivery", "Manage deliveries", "maternity", "delivery"),
        ("maternity:pnc", "Manage PNC records", "maternity", "pnc"),
        ("maternity:read", "View maternity records", "maternity", "read"),

        # Inventory
        ("inventory:read", "View inventory", "inventory", "read"),
        ("inventory:manage", "Manage inventory items", "inventory", "manage"),
        ("inventory:receive", "Receive stock", "inventory", "receive"),
        ("inventory:transfer", "Transfer stock", "inventory", "transfer"),
        ("inventory:count", "Perform stock counts", "inventory", "count"),

        # Reports & Analytics
        ("report:view", "View reports dashboard", "report", "view"),
        ("report:dhis2", "Generate DHIS2 reports", "report", "dhis2"),
        ("report:export", "Export reports", "report", "export"),
        ("report:analytics", "View analytics", "report", "analytics"),
        ("report:hmis", "Access HMIS reports", "report", "hmis"),

        # Admin
        ("admin:users", "Manage users", "admin", "users"),
        ("admin:roles", "Manage roles/permissions", "admin", "roles"),
        ("admin:facility", "Manage facility settings", "admin", "facility"),
        ("admin:system", "System configuration", "admin", "system"),
        ("admin:audit", "View audit logs", "admin", "audit"),
        ("admin:backup", "Manage backups", "admin", "backup"),
        ("admin:logs", "View system logs", "admin", "logs"),

        # Sync
        ("sync:manage", "Manage sync settings", "sync", "manage"),
        ("sync:monitor", "Monitor sync status", "sync", "monitor"),
        ("sync:force", "Force sync", "sync", "force"),

        # Community
        ("community:read", "View community data", "community", "read"),
        ("community:write", "Record community data", "community", "write"),
        ("community:manage", "Manage community programs", "community", "manage"),

        # AI/ML
        ("ai:inference", "Use AI inference", "ai", "inference"),
        ("ai:manage_models", "Manage AI models", "ai", "manage_models"),
        ("ai:view_telemetry", "View model telemetry", "ai", "view_telemetry"),
    ]
    for i, (code, name, resource, action) in enumerate(permissions, 1):
        op.execute(text(f"""
            INSERT INTO permissions (id, code, name, resource, action)
            VALUES ({i}, '{code}', '{name}', '{resource}', '{action}')
            ON CONFLICT (id) DO UPDATE SET code = '{code}', name = '{name}', resource = '{resource}', action = '{action}'
        """))


def _seed_roles() -> None:
    roles_data = [
        # id, name, description, system_role
        (1, "super_admin", "Full system access across all facilities and tenants", True),
        (2, "hospital_admin", "Administrative access for a hospital or facility", False),
        (3, "doctor", "Medical doctor with full clinical privileges", False),
        (4, "nurse", "Nursing staff", False),
        (5, "clinical_officer", "Clinical officer / medical licentiate", False),
        (6, "pharmacist", "Pharmacy staff", False),
        (7, "lab_technician", "Laboratory scientist / technician", False),
        (8, "lab_manager", "Laboratory manager", False),
        (9, "midwife", "Midwife (maternal and child health)", False),
        (10, "community_health_worker", "Community health worker (CHW)", False),
        (11, "data_entry", "Data entry clerk", False),
        (12, "moh_officer", "Ministry of Health officer (reporting access)", False),
        (13, "viewer", "Read-only access", False),
        (14, "epidemiologist", "Disease surveillance and outbreak response", False),
        (15, "facility_incharge", "Facility in-charge / sister-in-charge", False),
    ]
    for rid, name, desc, sys_role in roles_data:
        op.execute(text(f"""
            INSERT INTO roles (id, name, description, is_system_role)
            VALUES ({rid}, '{name}', '{desc}', {str(sys_role).lower()})
            ON CONFLICT (id) DO UPDATE SET name = '{name}', description = '{desc}'
        """))


def _seed_role_permissions() -> None:
    mapping = {
        "super_admin": list(range(1, 67)),
        "hospital_admin": [
            1,2,3,5,7, 8,13, 14,15,16,17,18, 20,21,26, 27,28,29,30,32,
            33,34,35,36,37,38, 39,40,41,42,43,44,45, 46,47,48,49,50,51,
            52,53,54,55,56,57, 63,64
        ],
        "facility_incharge": [
            1,2,3,5, 8,9,13,14, 17,18, 20,21,26, 27,28,32,
            33,34,35,36,37,38, 39,40,42,43, 46,47,48,49,50,51,
            53,54,56, 64
        ],
        "doctor": [1,2,3,5, 8,9,10,11,13, 14,15,16,17,18, 19,21, 26,27,28, 33,34,37],
        "clinical_officer": [1,2,3,5, 8,9,10,11,13, 14,15,16,17,18, 19,21, 26,27,28, 33,34,37],
        "nurse": [1,2,3,5, 8,9,13, 15, 20,21, 26,27,28,29, 33,34,37, 38,39,40,42, 56,57],
        "midwife": [1,2,3,5, 8,13, 15, 20,21, 26,27,28, 33,34,37,38,39,40,41,42],
        "pharmacist": [1, 27,28,29,30,31,32, 43,44,45],
        "lab_technician": [1, 20,21,22],
        "lab_manager": [1, 20,21,22,23,24,25],
        "epidemiologist": [1,5, 8,13, 20,21, 36, 46,47,48,49,50, 60,61,62],
        "community_health_worker": [1,2,5, 15, 20, 33,34,37, 56,57],
        "data_entry": [1,2,3,5, 11, 20, 27, 33,34, 39,42],
        "moh_officer": [1,5, 8,13, 20,21, 26, 33, 36, 46,47,48,49,50,51, 60,61,62, 64],
        "viewer": [1, 8, 20, 26, 33, 46],
    }
    for role_name, perm_ids in mapping.items():
        role_row = op.get_bind().execute(
            text(f"SELECT id FROM roles WHERE name = '{role_name}'")
        ).fetchone()
        if role_row:
            role_id = role_row[0]
            for pid in perm_ids:
                op.execute(text(f"""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES ({role_id}, {pid})
                    ON CONFLICT DO NOTHING
                """))


def _seed_default_users() -> None:
    # Password: all users have bcrypt hash of "ubuntucare2024!"
    pw_hash = "$2b$12$LJ3m4ys3Lg3YOCwLpWYqWOeWtGHiK5RJv7vJCU0qJ8y8wKQD.k0ba"

    users = [
        {
            "username": "admin",
            "email": "admin@ubuntucare.gov.zm",
            "first_name": "System",
            "last_name": "Admin",
            "phone": "+260977000001",
            "designation": "System Administrator",
            "roles": [1],
        },
        {
            "username": "uth_admin",
            "email": "uth.admin@uh.gov.zm",
            "first_name": "UTH",
            "last_name": "Administrator",
            "phone": "+260977000002",
            "designation": "Hospital Administrator",
            "facility_code": "UH001",
            "roles": [2],
        },
        {
            "username": "moh_officer",
            "email": "reports@moh.gov.zm",
            "first_name": "MoH",
            "last_name": "Reports",
            "phone": "+260977000003",
            "designation": "Ministry of Health Officer",
            "roles": [12],
        },
        {
            "username": "dr_mwamba",
            "email": "john.mwamba@uh.gov.zm",
            "first_name": "John",
            "last_name": "Mwamba",
            "phone": "+260977000004",
            "designation": "Senior Medical Officer",
            "facility_code": "UH001",
            "roles": [3],
        },
        {
            "username": "nurse_banda",
            "email": "grace.banda@uh.gov.zm",
            "first_name": "Grace",
            "last_name": "Banda",
            "phone": "+260977000005",
            "designation": "Registered Nurse Midwife",
            "facility_code": "UH001",
            "roles": [4, 9],
        },
        {
            "username": "chw_mulenga",
            "email": "peter.mulenga@chw.gov.zm",
            "first_name": "Peter",
            "last_name": "Mulenga",
            "phone": "+260977000006",
            "designation": "Community Health Worker",
            "facility_code": "KNW001",
            "roles": [10],
        },
        {
            "username": "pharm_tembo",
            "email": "alice.tembo@ndh.gov.zm",
            "first_name": "Alice",
            "last_name": "Tembo",
            "phone": "+260977000007",
            "designation": "Pharmacist",
            "facility_code": "NDH001",
            "roles": [6],
        },
        {
            "username": "lab_kasonde",
            "email": "brian.kasonde@uh.gov.zm",
            "first_name": "Brian",
            "last_name": "Kasonde",
            "phone": "+260977000008",
            "designation": "Chief Laboratory Scientist",
            "facility_code": "UH001",
            "roles": [7, 8],
        },
    ]

    for user_data in users:
        uid = str(uuid4())
        facility_clause = ""
        if "facility_code" in user_data:
            facility_clause = f"""
                ,(SELECT id FROM health_facilities WHERE code = '{user_data['facility_code']}')"""
        else:
            facility_clause = ", NULL"

        op.execute(text(f"""
            INSERT INTO users (id, username, email, password_hash, first_name, last_name,
                phone, designation, facility_id, is_active, is_verified, must_change_password)
            VALUES (
                '{uid}', '{user_data["username"]}', '{user_data["email"]}',
                '{pw_hash}', '{user_data["first_name"]}', '{user_data["last_name"]}',
                '{user_data["phone"]}', '{user_data["designation"]}'
                {facility_clause},
                true, true, false
            )
            ON CONFLICT (username) DO UPDATE SET updated_at = NOW()
        """))

        actual_uid = op.get_bind().execute(
            text("SELECT id FROM users WHERE username = '{u}'".format(u=user_data["username"]))
        ).fetchone()[0]

        for role_id in user_data["roles"]:
            op.execute(text(f"""
                INSERT INTO user_roles (user_id, role_id)
                VALUES ('{actual_uid}', {role_id})
                ON CONFLICT DO NOTHING
            """))


if __name__ == "__main__":
    upgrade()
