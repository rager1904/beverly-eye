"""Run remaining migrations (004-006)."""
import os
from alembic.config import Config
from alembic import command

url = os.environ.get("DATABASE_URL")
cfg = Config("scripts/migration/alembic.ini")
cfg.set_main_option("sqlalchemy.url", url)
command.upgrade(cfg, "head")
print("Migration complete!")
