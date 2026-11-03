"""Debug with config from ini file."""
import os
from alembic.script import ScriptDirectory
from alembic.script.base import Script
from alembic.config import Config

cfg = Config("scripts/migration/alembic.ini")
cfg.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL", ""))

s = ScriptDirectory.from_config(cfg)
print(f'version_locations: {s._version_locations}')
print(f'file_template: {s.file_template}')

vers = [v for v in s._version_locations if v.exists()]
print(f'existing locations: {vers}')

count = 0
for v in vers:
    for file_path in Script._list_py_dir(s, v):
        count += 1
        print(f'  file: {file_path}')
print(f'total py files: {count}')

scripts = list(s.walk_revisions())
print(f'walk_revisions: {len(scripts)}')
for scr in scripts:
    print(f'  {scr.revision} -> {scr.doc}')
