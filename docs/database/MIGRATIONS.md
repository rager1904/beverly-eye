# UbuntuCare Database Migrations Guide

## Alembic Setup

UbuntuCare uses **Alembic** for database schema migration management with PostgreSQL.

### Configuration

Migration scripts: `src/backend/migrations/`
Config file: `src/backend/migrations/alembic.ini`
Env file: `src/backend/migrations/env.py`

### Initial Setup

```bash
# Initialize Alembic (already done)
cd src/backend
alembic init migrations

# Configure alembic.ini
# sqlalchemy.url = postgresql+asyncpg://ubuntucare:password@localhost:5432/ubuntucare

# Create first migration
alembic revision --autogenerate -m "initial_schema"

# Apply
alembic upgrade head
```

---

## Migration Workflow

### Creating a New Migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "add_drug_supply_table"

# Review the generated migration
# Edit if needed (add data migration, custom SQL, etc.)

# Apply to development
alembic upgrade head

# Test rollback
alembic downgrade -1
```

### Migration Structure

```python
"""add drug supply chain tables

Revision ID: abc123def456
Revises: prev_revision_id
Create Date: 2026-06-17 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123def456'
down_revision = 'prev_revision_id'

def upgrade():
    op.create_table(
        'drug_inventory',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('drug_code', sa.String(length=50), nullable=False),
        sa.Column('drug_name', sa.String(length=300), nullable=False),
        sa.Column('batch_number', sa.String(length=100), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('unit_price_zmw', sa.Numeric(12, 2), nullable=True),
        sa.Column('hospital_id', sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_drug_inventory_hospital', 'drug_inventory', ['hospital_id'])
    op.create_index('idx_drug_inventory_expiry', 'drug_inventory', ['expiry_date'])

def downgrade():
    op.drop_table('drug_inventory')
```

---

## Zero-Downtime Migration Strategy

### Principles

1. **Never lock tables for writes** during production migrations
2. **Add columns as nullable** first, then backfill
3. **Create indexes CONCURRENTLY** (non-blocking)
4. **Use CHECK constraints** instead of NOT NULL for phased enforcement
5. **Dual-write** for schema changes that need data transformation

### Pattern: Add a NOT NULL Column

```python
# Step 1: Add as nullable
def upgrade_step1():
    op.add_column('patients', sa.Column('nhima_number', sa.String(50), nullable=True))

# Step 2: Backfill data (application-level, run separately)
# UPDATE patients SET nhima_number = ... WHERE nhima_number IS NULL;

# Step 3: Make NOT NULL
def upgrade_step2():
    op.alter_column('patients', 'nhima_number', nullable=False)
```

### Pattern: Create Index Without Downtime

```python
def upgrade():
    # CONCURRENTLY requires autocommit
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patients_phone "
        "ON patients (phone)"
    )
```

### Pattern: Rename a Column

```python
def upgrade():
    # Step 1: Add new column
    op.add_column('patients', sa.Column('phone_number_new', sa.String(20)))

    # Step 2: Dual-write at application level (both columns updated)

    # Step 3: Backfill old → new
    op.execute("UPDATE patients SET phone_number_new = phone WHERE phone_number_new IS NULL")

    # Step 4: Drop old column
    op.drop_column('patients', 'phone')
    op.rename('patients', 'phone_number_new', 'phone')
```

---

## Rollback Procedures

### Standard Rollback

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123def456

# Rollback to beginning
alembic downgrade base
```

### Emergency Rollback

```bash
# 1. Stop application traffic to affected service
# 2. Rollback database
alembic downgrade -1

# 3. Rollback application deployment to previous version
kubectl rollout undo deployment/emr-service

# 4. Verify health
curl http://localhost:8001/health

# 5. Resume traffic
```

### Failed Migration Recovery

```bash
# If a migration fails mid-flight:
# 1. PostgreSQL auto-rolls back the failed transaction
# 2. Verify database is at previous state
alembic current

# 3. Fix migration script
# 4. Re-apply
alembic upgrade head
```

---

## Data Seeding

### Seed Scripts

Location: `src/backend/migrations/seed/`

```bash
# Run seed scripts
python -m migrations.seed.facilities
python -m migrations.seed.icd10_codes
python -m migrations.seed.zambia_eml
python -m migrations.seed.vaccine_schedule
python -m migrations.seed.admin_users
```

### Available Seeds

| Seed | Source | Purpose |
|------|--------|---------|
| `facilities.py` | MoH HMIS registry | All Zambia health facilities |
| `icd10_codes.py` | WHO ICD-10 | ICD-10-CM code database |
| `zambia_eml.py` | MoH Essential Medicines List | Zambia EML with pricing |
| `vaccine_schedule.py` | Zambia EPI | National immunization schedule |
| `admin_users.py` | Keycloak | Initial admin accounts |
| `provinces.py` | MoH | Province/district reference data |
| `disease_list.py` | ZNPHI | Notifiable disease list |
| `lab_tests.py` | MoH lab catalog | Standard lab test catalog |

### Data Seeding Workflow

```bash
# Full setup for new deployment
alembic upgrade head
python -m migrations.seed.run_all

# Verify seeding
python -m migrations.seed.verify
```
