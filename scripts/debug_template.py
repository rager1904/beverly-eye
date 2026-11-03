"""Debug alembic file template."""
import os
from alembic.script import ScriptDirectory
from alembic.config import Config

cfg = Config()
cfg.set_main_option('script_location', 'data/migrations')
s = ScriptDirectory.from_config(cfg)

print(f'file_template: {repr(s.file_template)}')

# Read the actual ini file
from configparser import ConfigParser
parser = ConfigParser()
parser.read('scripts/migration/alembic.ini')
print(f'ini file_template: {repr(parser.get("alembic", "file_template"))}')

# Try to manually regex
import re
template = s.file_template
# Convert to regex
pattern = template.replace('%(rev)s', '(?P<rev>[^_]+)').replace('%(slug)s', '(?P<slug>[^_]+)')
pattern = '^' + re.escape(pattern) + r'\.py$'
print(f'pattern: {pattern}')

test_files = ['001_initial_schema.py', '002_seed_zambia_data.py']
for f in test_files:
    m = re.match(pattern, f)
    print(f'{f}: {m}')
