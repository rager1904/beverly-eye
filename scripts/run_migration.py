"""Run migrations with env var override."""
import os
from alembic.config import Config
from alembic import command

url = os.environ.get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL env var not set")

print(f"Using DATABASE_URL: {url}")

cfg = Config("scripts/migration/alembic.ini")
cfg.set_main_option("sqlalchemy.url", url)

print(f"Running alembic upgrade head...")
command.upgrade(cfg, "head")
print("Migration complete!")
