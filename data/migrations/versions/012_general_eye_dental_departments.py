"""Align the default clinic directory to General, Eye, and Dental.

Revision ID: 012
Revises: 011
Create Date: 2026-10-31
"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "012"
down_revision: Optional[str] = "011"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None

DEFAULT_HOSPITAL_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    # Keep specialty-specific rows for history, but remove them from active
    # routing. The facility's active directory is exactly these three.
    op.execute(
        sa.text(
            f"""UPDATE departments
                SET name = 'Eye', location = 'Eye clinic', is_active = TRUE
                WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid AND code = 'EYE'"""
        )
    )
    op.execute(
        sa.text(
            f"""UPDATE departments
                SET name = 'Dental', location = 'Dental clinic', is_active = TRUE
                WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid AND code = 'DENT'"""
        )
    )
    op.execute(
        sa.text(
            f"""UPDATE departments
                SET is_active = FALSE
                WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid
                  AND code IN ('OPT', 'OMS')"""
        )
    )
    op.execute(
        sa.text(
            f"""INSERT INTO departments (id, name, code, location, hospital_id, is_active)
                SELECT gen_random_uuid(), 'General', 'GEN', 'General clinic',
                       '{DEFAULT_HOSPITAL_ID}'::uuid, TRUE
                WHERE EXISTS (
                    SELECT 1 FROM hospitals
                    WHERE id = '{DEFAULT_HOSPITAL_ID}'::uuid
                )
                  AND NOT EXISTS (
                    SELECT 1 FROM departments
                    WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid
                      AND code = 'GEN'
                )"""
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""UPDATE departments
                SET name = 'Ophthalmology', location = 'Eye clinic', is_active = TRUE
                WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid AND code = 'EYE'"""
        )
    )
    op.execute(
        sa.text(
            f"""UPDATE departments
                SET name = 'Dental Clinic', location = 'General dentistry and oral health', is_active = TRUE
                WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid AND code = 'DENT'"""
        )
    )
    op.execute(
        sa.text(
            f"""UPDATE departments
                SET is_active = TRUE
                WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid
                  AND code IN ('OPT', 'OMS')"""
        )
    )
    op.execute(
        sa.text(
            f"""UPDATE departments
                SET is_active = FALSE
                WHERE hospital_id = '{DEFAULT_HOSPITAL_ID}'::uuid AND code = 'GEN'"""
        )
    )
