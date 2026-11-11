"""Store structured Eye Clinic details on clinical notes."""

import sqlalchemy as sa
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clinical_notes", sa.Column("eye_details", sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError("Downgrading would discard saved Eye Clinic details.")
