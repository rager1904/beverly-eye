import os
from alembic.config import Config
cfg = Config("scripts/migration/alembic.ini")
url = cfg.get_main_option("sqlalchemy.url")
print(f"Alembic URL: {repr(url)}")
print(f"From env: {repr(os.environ.get('DATABASE_URL', 'NOT SET'))}")
