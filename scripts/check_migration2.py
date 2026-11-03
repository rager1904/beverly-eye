"""Debug migration scripts."""
import os
from alembic.config import Config
from alembic.script import ScriptDirectory

url = os.environ.get("DATABASE_URL")
cfg = Config("scripts/migration/alembic.ini")
cfg.set_main_option("sqlalchemy.url", url)

script = ScriptDirectory.from_config(cfg)
print(f"Script dir: {script.dir}")
print(f"Scripts: {[s.path for s in script.walk_revisions()]}")

try:
    heads = script.get_heads()
    print(f"Heads: {heads}")
except Exception as e:
    print(f"get_heads error: {e}")
    import traceback
    traceback.print_exc()
