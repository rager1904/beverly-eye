"""PostgreSQL SQL-generation checks for revision 008's two supported baselines.

These use real SQLAlchemy/Alembic compilers, not a running PostgreSQL server.
"""
import importlib.util
from pathlib import Path
import types
import unittest
from unittest.mock import patch

try:
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
except ImportError:
    sa = None

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipIf(sa is None, 'Requires sqlalchemy and alembic')
class OrderWorkflowMigrationTests(unittest.TestCase):
    def execute_revision(self, existing=False):
        spec = importlib.util.spec_from_file_location('revision008', ROOT / 'data/migrations/versions/008_lab_order_workflow.py')
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        statements = []
        def execute(sql, *args, **kwargs):
            statements.append(str(sql.compile(dialect=engine.dialect)))
        engine = sa.create_mock_engine('postgresql://', execute)
        migration.op = Operations(MigrationContext.configure(connection=engine))
        tables = ['patients', 'lab_orders', 'lab_results']
        if existing:
            tables += ['encounters', 'orders', 'results']
        order_columns = ['id', 'status', 'hospital_id']
        if existing:
            order_columns += ['specimen_type', 'specimen_id', 'collected_by', 'collected_datetime', 'received_by', 'received_datetime', 'verified_by', 'verified_datetime']
        inspector = types.SimpleNamespace(
            get_table_names=lambda: tables,
            get_columns=lambda name: [{'name': c} for c in (order_columns if name == 'orders' else (['verified_by', 'verified_datetime'] if existing else ['id']))],
            get_indexes=lambda name: [{'name': 'idx_orders_specimen_id'}] if existing else [],
            get_unique_constraints=lambda name: [{'name': 'uq_orders_hospital_specimen'}] if existing else [],
        )
        def create_enum(enum, bind, checkfirst=False):
            self.assertTrue(checkfirst)
            if not existing:
                statements.append(str(postgresql.CreateEnumType(enum).compile(dialect=engine.dialect)))
        with patch.object(migration.sa, 'inspect', return_value=inspector), patch.object(postgresql.ENUM, 'create', create_enum):
            migration.upgrade()
        return statements

    def test_legacy_schema_creates_order_prerequisites_before_workflow(self):
        statements = self.execute_revision()
        sql = '\n'.join(statements)
        self.assertLess(sql.index('CREATE TYPE orderstatus'), sql.index('ALTER TYPE orderstatus'))
        self.assertLess(sql.index('CREATE TABLE orders'), sql.index('ALTER TABLE orders ADD COLUMN specimen_type'))
        self.assertLess(sql.index('CREATE TABLE encounters'), sql.index('CREATE TABLE orders'))
        self.assertLess(sql.index('CREATE TABLE orders'), sql.index('CREATE TABLE results'))
        self.assertIn('FOREIGN KEY(patient_id) REFERENCES patients (id)', sql)
        self.assertIn('UNIQUE (hospital_id, specimen_id)', sql)
        self.assertNotIn('DROP ', sql)
        self.assertNotIn('ALTER TABLE lab_orders', sql)
        self.assertNotIn('ALTER TABLE lab_results', sql)

    def test_existing_orm_schema_does_not_recreate_or_drop_data(self):
        statements = self.execute_revision(existing=True)
        self.assertEqual(len(statements), 3)
        for sql in statements:
            self.assertIn('ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS', sql)


if __name__ == '__main__':
    unittest.main()
