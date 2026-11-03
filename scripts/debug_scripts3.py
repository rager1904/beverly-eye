"""Detailed debug of ScriptDirectory."""
import os
from pathlib import Path
from alembic.script import ScriptDirectory
from alembic.script.base import Script, _only_source_rev_file
from alembic import util
from alembic.config import Config

cfg = Config()
cfg.set_main_option('script_location', 'data/migrations')
s = ScriptDirectory.from_config(cfg)

vers = [v for v in s._version_locations if v.exists()]
print(f'version_locations: {vers}')

for v in vers:
    print(f'Listing {v}:')
    count = 0
    for file_path in Script._list_py_dir(s, v):
        count += 1
        real_path = file_path.resolve()
        print(f'  Found: {file_path} -> {real_path}')
        filename = file_path.name
        match = _only_source_rev_file.match(filename)
        print(f'    match: {match}')
        if match:
            print(f'    group1: {match.group(1)}')
            try:
                module = util.load_python_file(v, filename)
                print(f'    has revision: {hasattr(module, "revision")}')
                if hasattr(module, "revision"):
                    print(f'    revision: {module.revision}')
            except Exception as e:
                print(f'    load error: {e}')
    print(f'Total files found: {count}')
