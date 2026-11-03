"""Debug script directory parsing - try direct import."""
import os
import sys
sys.path.insert(0, 'data/migrations')

from alembic.script import ScriptDirectory
from alembic.script.base import Script
from alembic.config import Config

cfg = Config()
cfg.set_main_option('script_location', 'data/migrations')
s = ScriptDirectory.from_config(cfg)
print('dir:', repr(s.dir))
print('exists:', os.path.isdir(s.dir))

# Debug inside ScriptDirectory._load_revisions
files = sorted(os.listdir(s.dir))
py_files = [f for f in files if f.endswith('.py') and f not in ('env.py', '__init__.py')]
print('py_files:', py_files)

for f in py_files:
    path = os.path.join(s.dir, f)
    print(f'file: {f}')
    # Read and exec to extract revision
    with open(path) as fh:
        source = fh.read()
    # Find revision line
    for line in source.split('\n'):
        if line.strip().startswith('revision:'):
            print(f'  {line.strip()}')
        if line.strip().startswith('down_revision:'):
            print(f'  {line.strip()}')

# Try to create Script objects
try:
    scripts = list(s.walk_revisions())
    print(f'walk_revisions: {len(scripts)} scripts')
    for scr in scripts:
        print(f'  {scr.revision} -> {scr.doc}')
except Exception as e:
    print(f'walk error: {e}')
