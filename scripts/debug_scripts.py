"""Debug script directory parsing."""
import os
from alembic.script import ScriptDirectory
from alembic.script.base import _cget
from alembic.config import Config

cfg = Config()
cfg.set_main_option('script_location', 'data/migrations')
s = ScriptDirectory.from_config(cfg)
print('dir:', s.dir)
print('exists:', os.path.isdir(s.dir))
files = os.listdir(s.dir)
print('all files:', files)
py_files = [f for f in files if f.endswith('.py') and f not in ('env.py', '__init__.py') and not f.startswith('__')]
print('py files:', py_files)

for f in py_files:
    path = os.path.join(s.dir, f)
    print(f'Trying to load: {f}')
    try:
        revision = _cget(path, 'revision')
        down_revision = _cget(path, 'down_revision')
        print(f'  revision={revision}, down_revision={down_revision}')
    except Exception as e:
        print(f'  error: {e}')
