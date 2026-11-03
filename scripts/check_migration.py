"""Check alembic migration state."""
import os
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory

url = os.environ.get("DATABASE_URL")
cfg = Config("scripts/migration/alembic.ini")
cfg.set_main_option("sqlalchemy.url", url)

# Show current head
script = ScriptDirectory.from_config(cfg)
heads = script.get_heads()
print(f"Head revisions: {heads}")

# Show current state
try:
    command.current(cfg)
except Exception as e:
    print(f"current() error: {e}")

# Show history
try:
    command.history(cfg)
except Exception as e:
    print(f"history() error: {e}")
