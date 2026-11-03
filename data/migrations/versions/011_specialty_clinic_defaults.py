"""Configure the default facility for ophthalmology and dental services.

Revision ID: 011
Revises: 010
Create Date: 2026-10-31
"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "011"
down_revision: Optional[str] = "010"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None

DEFAULT_HOSPITAL_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_DEPARTMENTS = (
    ("Ophthalmology", "EYE", "Eye clinic"),
    ("Optometry", "OPT", "Vision testing and optical services"),
    ("Dental Clinic", "DENT", "General dentistry and oral health"),
    ("Oral & Maxillofacial Surgery", "OMS", "Oral surgery"),
)


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE hospitals
            SET name = 'Eye & Dental Hospital',
                code = 'EDH001',
                level = 'specialized_hospital',
                updated_at = now()
            WHERE id = '{DEFAULT_HOSPITAL_ID}'::uuid
            """
        )
    )

    for name, code, location in DEFAULT_DEPARTMENTS:
        op.execute(
            sa.text(
                f"""
                INSERT INTO departments (id, name, code, location, hospital_id, is_active)
                SELECT gen_random_uuid(), '{name}', '{code}', '{location}',
                       '{DEFAULT_HOSPITAL_ID}'::uuid, TRUE
                WHERE EXISTS (
                    SELECT 1 FROM hospitals
                    WHERE id = '{DEFAULT_HOSPITAL_ID}'::uuid
                )
                  AND NOT EXISTS (
                    SELECT 1 FROM departments
                    WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid
                      AND code = '{code}'
                )
                """
            )
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DELETE FROM departments
            WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid
              AND code IN ('EYE', 'OPT', 'DENT', 'OMS')
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE hospitals
            SET name = 'University Teaching Hospital',
                code = 'UTH001',
                level = 'tertiary_hospital',
                updated_at = now()
            WHERE id = '{DEFAULT_HOSPITAL_ID}'::uuid
            """
        )
    )
