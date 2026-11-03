"""Native, ephemeral UbuntuCare demo inside Google Colab (no Docker/systemd).

Only the frontend is tunneled. All databases, auth and model services bind to
loopback. This deliberately refuses to run on the user's Windows computer.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from asgi import SERVICES, selected_services

DOWNLOADS = {
    'keycloak': ('https://github.com/keycloak/keycloak/releases/download/23.0.7/keycloak-23.0.7.tar.gz', 'keycloak.tar.gz'),
    'qdrant': ('https://github.com/qdrant/qdrant/releases/download/v1.13.4/qdrant-x86_64-unknown-linux-gnu.tar.gz', 'qdrant.tar.gz'),
    'ollama': ('https://github.com/ollama/ollama/releases/download/v0.6.2/ollama-linux-amd64.tgz', 'ollama.tar.gz'),
    'neo4j': ('https://dist.neo4j.org/neo4j-community-5.26.0-unix.tar.gz', 'neo4j.tar.gz'),
    'node': ('https://nodejs.org/dist/v20.19.0/node-v20.19.0-linux-x64.tar.xz', 'node.tar.xz'),
    'go': ('https://go.dev/dl/go1.24.2.linux-amd64.tar.gz', 'go.tar.gz'),
    'minio-source': ('https://github.com/minio/minio/archive/refs/tags/RELEASE.2025-04-22T22-12-26Z.tar.gz', 'minio.tar.gz'),
    'cloudflared': ('https://github.com/cloudflare/cloudflared/releases/download/2025.2.1/cloudflared-linux-amd64', 'cloudflared'),
}


def require_colab():
    if sys.platform != 'linux' or platform.machine() not in {'x86_64', 'amd64'} or not Path('/content').is_dir():
        raise RuntimeError('This launcher runs inside a Linux x86-64 Google Colab runtime only; it never starts local Docker.')
    if os.geteuid() != 0:
        raise RuntimeError('Colab root access is required to install native PostgreSQL and Redis.')
    if not (os.environ.get('COLAB_RELEASE_TAG') or 'google.colab' in sys.modules):
        raise RuntimeError('Run this from a Google Colab notebook, not a local machine.')


def available_memory_gib():
    values = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    total = int(values['MemTotal'].split()[0]) * 1024
    for path in ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes'):
        try:
            limit = Path(path).read_text().strip()
            if limit != 'max':
                total = min(total, int(limit))
        except (OSError, ValueError):
            pass
    return total / 1024**3


def fetch(url, destination):
    destination = Path(destination)
    if destination.exists() and destination.stat().st_size:
        return destination
    temporary = destination.with_suffix(destination.suffix + '.partial')
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
        shutil.copyfileobj(response, output)
    temporary.replace(destination)
    return destination


def extract(archive, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as bundle:
        # Reject traversal and device entries; Python's data filter also checks links.
        bundle.extractall(destination, filter='data')


class ColabRuntime:
    def __init__(self, root='/content/ubuntucare-native', enable_ai=False):
        require_colab()
        self.enable_ai = bool(enable_ai)
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.logs = self.root / 'logs'
        self.logs.mkdir(mode=0o700, exist_ok=True)
        self.processes = {}
        self.env = os.environ.copy()
        self.env.pop('PYTHONHOME', None)
        self.env['UBUNTUCARE_COLAB_ENABLE_AI'] = '1' if self.enable_ai else '0'
        self.env.update(PYTHONPATH=str(REPO), PYTHONUNBUFFERED='1', OMP_NUM_THREADS='2', TOKENIZERS_PARALLELISM='false')
        self.python = self.root / 'venv-system/bin/python'
        self.frontend_url = None
        tools = self.root / 'tools'
        self.env['PATH'] = f'{tools}/node-v20.19.0-linux-x64/bin:{tools}/go/bin:{self.python.parent}:' + self.env['PATH']
        self.env['GOPATH'] = str(self.root / 'go-cache')
        secret_file = self.root / 'secrets.json'
        if secret_file.exists():
            private = json.loads(secret_file.read_text())
        else:
            private = {key: secrets.token_hex(24) for key in ('db_password', 'secret_key', 'kc_admin', 'kc_client', 'minio', 'neo4j')}
            fd = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                json.dump(private, stream)
        self.private = private
        db_url = f"postgresql+asyncpg://ubuntucare:{private['db_password']}@127.0.0.1:55432/ubuntucare"
        self.env.update({
            'ENVIRONMENT': 'development', 'SECRET_KEY': private['secret_key'], 'DATABASE_URL': db_url,
            'POSTGRES_HOST': '127.0.0.1', 'POSTGRES_PORT': '55432', 'POSTGRES_USER': 'ubuntucare',
            'POSTGRES_DB': 'ubuntucare', 'POSTGRES_PASSWORD': private['db_password'],
            'CELERY_BROKER_URL': 'redis://127.0.0.1:56379/0', 'CELERY_RESULT_BACKEND': 'redis://127.0.0.1:56379/0',
            'REDIS_URL': 'redis://127.0.0.1:56379/0', 'REDIS_HOST': '127.0.0.1', 'REDIS_PORT': '56379',
            'KEYCLOAK_SERVER_URL': 'http://127.0.0.1:8081', 'KEYCLOAK_REALM': 'ubuntucare',
            'KEYCLOAK_CLIENT_ID': 'api-gateway', 'KEYCLOAK_CLIENT_SECRET': private['kc_client'],
            'KEYCLOAK_ADMIN_USER': 'admin', 'KEYCLOAK_ADMIN': 'admin',
            'KEYCLOAK_ADMIN_PASSWORD': private['kc_admin'], 'KEYCLOAK_DEMO_USER_PASSWORD': 'UbuntuCare2024!',
            'KC_DB': 'postgres', 'KC_DB_URL': 'jdbc:postgresql://127.0.0.1:55432/ubuntucare_keycloak',
            'KC_DB_USERNAME': 'ubuntucare', 'KC_DB_PASSWORD': private['db_password'],
            'JAVA_OPTS_KC_HEAP': '-Xms64m -Xmx384m',
            'NEO4J_URI': 'bolt://127.0.0.1:7687', 'NEO4J_USER': 'neo4j', 'NEO4J_PASSWORD': private['neo4j'],
            'MINIO_ENDPOINT': '127.0.0.1:9000', 'MINIO_ACCESS_KEY': 'ubuntucare', 'MINIO_ROOT_USER': 'ubuntucare',
            'MINIO_SECRET_KEY': private['minio'], 'MINIO_ROOT_PASSWORD': private['minio'],
            'QDRANT_HOST': '127.0.0.1', 'WHISPER_MODEL_SIZE': 'tiny', 'WHISPER_DEVICE': 'cpu',
            'WHISPER_COMPUTE_TYPE': 'int8', 'HF_HOME': str(self.root / 'models/huggingface'),
            'OLLAMA_HOST': '127.0.0.1:11434', 'OLLAMA_MODELS': str(self.root / 'models/ollama'),
            'OLLAMA_NUM_PARALLEL': '1', 'OLLAMA_MAX_LOADED_MODELS': '1',
            'API_INTERNAL_URL': 'http://127.0.0.1:8000', 'NEXT_PUBLIC_API_URL': '/api/v1',
            'NEXT_TELEMETRY_DISABLED': '1', 'NODE_ENV': 'production',
            'ENV_FILE': str(self.root / 'keycloak.env'),
        })
        # Private setup output is never displayed: it contains generated credentials.
        env_file = Path(self.env['ENV_FILE'])
        if not env_file.exists():
            fd = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)

    def run(self, args, name, timeout=1800, env=None, cwd=None, input=None):
        path = self.logs / (name + '.log')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        print(f'{name} ...', flush=True)
        with os.fdopen(fd, 'w') as output:
            result = subprocess.run([str(a) for a in args], cwd=cwd or REPO, env=env or self.env,
                                    input=input, text=True, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode:
            safe_steps = {'apt-update', 'apt-install', 'python-environment', 'python-environment-check',
                          'python-environment-fallback', 'virtualenv-bootstrap', 'pip-bootstrap',
                          'python-dependencies', 'python-ai-dependencies', 'torch-install'}
            if name in safe_steps:
                tail = '\n'.join(path.read_text(errors='replace').splitlines()[-18:])
                for value in getattr(self, 'private', {}).values():
                    tail = tail.replace(value, '[REDACTED]')
                # Redact credential-bearing URLs from private package indexes/proxies.
                tail = re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@', r'\1[REDACTED]@', tail)
                print(tail, flush=True)
            raise RuntimeError(f'{name} failed (exit {result.returncode}). Inspect private log: {path}')
        return result

    def start(self, name, args, env=None, cwd=None, port=None):
        existing = self.processes.get(name)
        if existing and existing.poll() is None:
            return existing
        if port:
            with socket.socket() as probe:
                if probe.connect_ex(('127.0.0.1', port)) == 0:
                    raise RuntimeError(f'{name}: port {port} is occupied by a process not owned by this launcher. Use a fresh Colab runtime.')
        fd = os.open(self.logs / (name + '.log'), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as output:
            process = subprocess.Popen([str(a) for a in args], cwd=cwd or REPO, env=env or self.env,
                                       stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        self.processes[name] = process
        print(f'Started {name}', flush=True)
        return process

    def wait_http(self, name, url, timeout=180, healthy=None):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            process = self.processes.get(name)
            if process and process.poll() is not None:
                raise RuntimeError(f'{name} exited. Inspect {self.logs / (name + ".log")}')
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.status == 200:
                        data = response.read()
                        if healthy is None or healthy(json.loads(data)):
                            print(f'Ready: {name}', flush=True)
                            return
            except (OSError, ValueError):
                pass
            time.sleep(2)
        raise RuntimeError(f'{name} did not become ready at {url}; inspect {self.logs / (name + ".log")}')

    def create_python_environment(self):
        # Colab's kernel can be a custom /usr/local Python, while apt's
        # python3-venv supplies ensurepip only for /usr/bin/python3.
        # Do not reuse the partial kernel-created 'venv' from older launchers.
        system_python = Path('/usr/bin/python3')
        if not system_python.is_file():
            raise RuntimeError('System Python is missing after apt-install; inspect logs/apt-install.log.')
        clean_env = dict(self.env)
        clean_env.pop('PYTHONHOME', None)
        clean_env.pop('PYTHONPATH', None)
        destination = self.root / 'venv-system'
        try:
            self.run([system_python, '-m', 'venv', destination], 'python-environment', env=clean_env)
            self.python = destination / 'bin/python'
            self.run([self.python, '-m', 'pip', '--version'], 'python-environment-check', env=clean_env)
        except RuntimeError:
            # virtualenv carries pip wheels and does not depend on ensurepip.
            # Install the builder into a separate directory, never the kernel.
            bootstrap = self.root / 'virtualenv-bootstrap'
            self.run([sys.executable, '-m', 'pip', 'install', '--target', bootstrap,
                      'virtualenv==20.29.3'], 'virtualenv-bootstrap', env=clean_env)
            builder_env = dict(clean_env, PYTHONPATH=str(bootstrap))
            destination = self.root / 'venv-fallback'
            self.run([sys.executable, '-m', 'virtualenv', '--python', system_python,
                      destination], 'python-environment-fallback', env=builder_env)
            self.python = destination / 'bin/python'
            self.run([self.python, '-m', 'pip', '--version'], 'python-environment-check', env=clean_env)
        self.env['PATH'] = str(self.python.parent) + os.pathsep + self.env['PATH']
        print('Service Python environment ready (separate from the Colab kernel).', flush=True)

    def configure_hosts(self):
        hosts = Path('/etc/hosts')
        aliases = '127.0.0.1 emr api-gateway agent-orchestrator asr tts rag postgres redis qdrant neo4j minio host.docker.internal # ubuntucare-native\n'
        if '# ubuntucare-native' not in hosts.read_text():
            with hosts.open('a') as stream:
                stream.write('\n' + aliases)

    def app_services(self):
        return selected_services(self.enable_ai)

    def downloads(self):
        ai_tools = {'qdrant', 'neo4j', 'ollama'}
        return {name: item for name, item in DOWNLOADS.items() if self.enable_ai or name not in ai_tools}

    def install(self):
        memory = available_memory_gib()
        free_disk = shutil.disk_usage(self.root).free / 1024**3
        print(f'Colab RAM limit: {memory:.1f} GiB; free disk: {free_disk:.1f} GiB', flush=True)
        min_memory, min_disk = (10, 25) if self.enable_ai else (4, 10)
        if memory < min_memory or free_disk < min_disk:
            raise RuntimeError(f'This Colab demo configuration needs at least {min_memory} GiB RAM and {min_disk} GiB free disk.')
        self.run(['apt-get', 'update', '-qq'], 'apt-update')
        self.run(['apt-get', 'install', '-y', '-qq', 'postgresql', 'postgresql-contrib', 'postgresql-server-dev-all',
                  'redis-server', 'openjdk-17-jre-headless', 'python3', 'python3-venv', 'build-essential', 'git', 'curl',
                  'xz-utils'], 'apt-install')
        if self.enable_ai:
            self.run(['apt-get', 'install', '-y', '-qq', 'ffmpeg', 'libsndfile1', 'espeak-ng'], 'apt-ai-install')
        self.create_python_environment()
        self.run([self.python, '-m', 'pip', 'install', '--upgrade', 'pip'], 'pip-bootstrap')
        # CPU wheels avoid downloading gigabytes of unused CUDA dependencies.
        if self.enable_ai:
            self.run([self.python, '-m', 'pip', 'install', 'torch==2.6.0', '--index-url', 'https://download.pytorch.org/whl/cpu'], 'torch-install')
        self.run([self.python, '-m', 'pip', 'install', '-r', HERE / 'requirements.txt'], 'python-dependencies')
        if self.enable_ai:
            self.run([self.python, '-m', 'pip', 'install', '-r', HERE / 'requirements.ai.txt'], 'python-ai-dependencies')
        packages = self.root / 'downloads'
        packages.mkdir(exist_ok=True)
        for name, (url, filename) in self.downloads().items():
            print(f'Downloading {name} from official publisher ...', flush=True)
            archive = fetch(url, packages / filename)
            if name == 'cloudflared':
                archive.chmod(0o755)
            else:
                marker = packages / (name + '.extracted')
                if not marker.exists():
                    extract(archive, self.root / 'tools')
                    marker.touch()
        tools = self.root / 'tools'
        self.env['PATH'] = f'{tools}/node-v20.19.0-linux-x64/bin:{tools}/go/bin:{self.python.parent}:' + self.env['PATH']
        self.env['GOPATH'] = str(self.root / 'go-cache')
        self.run(['go', 'build', '-o', tools / 'minio', '.'], 'minio-build', cwd=tools / 'minio-RELEASE.2025-04-22T22-12-26Z')
        vector_source = self.root / 'pgvector'
        if not vector_source.exists():
            self.run(['git', 'clone', '--depth', '1', '--branch', 'v0.8.0', 'https://github.com/pgvector/pgvector.git', vector_source], 'pgvector-download')
        self.run(['make'], 'pgvector-build', cwd=vector_source)
        self.run(['make', 'install'], 'pgvector-install', cwd=vector_source)
        self.configure_hosts()
        frontend = REPO / 'src/frontend/web'
        self.run(['npm', 'ci', '--no-audit', '--no-fund'], 'frontend-dependencies', cwd=frontend)
        self.run(['npm', 'run', 'build'], 'frontend-build', cwd=frontend)
        # Import checks catch unresolved dependencies before any tunnel is exposed.
        for name, (module, _) in self.app_services().items():
            self.run([self.python, '-c', f'import {module}'], 'import-' + name)
        print('Native dependencies installed. No Docker daemon or remote URL is used.', flush=True)

    def start_data(self):
        versions = sorted(Path('/usr/lib/postgresql').iterdir(), key=lambda p: int(p.name))
        postgres_bin = versions[-1] / 'bin'
        data = self.root / 'postgres'
        data.mkdir(exist_ok=True)
        self.root.chmod(0o711)  # postgres may traverse to its private 0700 data directory
        self.run(['chown', '-R', 'postgres:postgres', data], 'postgres-owner')
        if not (data / 'PG_VERSION').exists():
            self.run(['runuser', '-u', 'postgres', '--', postgres_bin / 'initdb', '-D', data,
                      '--auth-local=trust', '--auth-host=scram-sha-256'], 'postgres-init')
        self.start('postgres', ['runuser', '-u', 'postgres', '--', postgres_bin / 'postgres', '-D', data,
                               '-h', '127.0.0.1', '-p', '55432', '-k', str(data), '-c', 'shared_buffers=128MB'], port=55432)
        for _ in range(60):
            check = subprocess.run([postgres_bin / 'pg_isready', '-h', '127.0.0.1', '-p', '55432'], stdout=subprocess.DEVNULL)
            if check.returncode == 0:
                break
            time.sleep(2)
        else:
            raise RuntimeError('PostgreSQL did not become ready; see logs/postgres.log')
        sql = "SELECT 'CREATE ROLE ubuntucare LOGIN SUPERUSER' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='ubuntucare')\\gexec\n"
        sql += f"ALTER ROLE ubuntucare PASSWORD '{self.private['db_password']}';\n"
        for database in ('ubuntucare', 'ubuntucare_keycloak'):
            sql += f"SELECT 'CREATE DATABASE {database} OWNER ubuntucare' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='{database}')\\gexec\n"
        # Password is stdin, never a process argument or notebook output.
        self.run(['runuser', '-u', 'postgres', '--', 'psql', '-h', data, '-v', 'ON_ERROR_STOP=1'], 'database-users', input=sql)
        self.start('redis', ['redis-server', '--bind', '127.0.0.1', '--port', '56379', '--dir', self.root,
                             '--save', '', '--appendonly', 'no'], port=56379)
        self.run([self.python, '-m', 'alembic', '-c', 'scripts/migration/alembic.ini', 'upgrade', 'head'], 'database-migrations')
        tools = self.root / 'tools'
        kc = tools / 'keycloak-23.0.7/bin/kc.sh'
        self.start('keycloak', [kc, 'start-dev', '--http-host=127.0.0.1', '--http-port=8081'], port=8081)
        self.wait_http('keycloak', 'http://127.0.0.1:8081/realms/master', timeout=300)
        self.run([self.python, 'scripts/setup/setup_keycloak.py'], 'keycloak-setup')
        # setup may select an existing client secret; reuse what it actually wrote.
        for line in Path(self.env['ENV_FILE']).read_text().splitlines():
            if line.startswith('KEYCLOAK_CLIENT_SECRET='):
                self.env['KEYCLOAK_CLIENT_SECRET'] = line.split('=', 1)[1].strip()
        if self.enable_ai:
            qconfig = self.root / 'qdrant.yaml'
            qconfig.write_text(f'storage:\n  storage_path: {self.root}/qdrant-data\nservice:\n  host: 127.0.0.1\n  http_port: 6333\n  grpc_port: 6334\ntelemetry_disabled: true\n')
            self.start('qdrant', [tools / 'qdrant', '--config-path', qconfig], port=6333)
            self.wait_http('qdrant', 'http://127.0.0.1:6333/healthz')
            neo = tools / 'neo4j-community-5.26.0'
            conf = neo / 'conf/neo4j.conf'
            conf.write_text('server.default_listen_address=127.0.0.1\nserver.memory.heap.initial_size=128m\nserver.memory.heap.max_size=384m\nserver.memory.pagecache.size=128m\nserver.bolt.listen_address=127.0.0.1:7687\nserver.http.listen_address=127.0.0.1:7474\n')
            if not (neo / 'data/dbms/auth.ini').exists():
                # neo4j-admin supports stdin only through env-configured import; use env auth for first start instead.
                self.run([neo / 'bin/neo4j-admin', 'dbms', 'set-initial-password', self.private['neo4j']], 'neo4j-password')
            self.start('neo4j', [neo / 'bin/neo4j', 'console'], port=7474)
            self.wait_http('neo4j', 'http://127.0.0.1:7474', timeout=180)
        self.start('minio', [tools / 'minio', 'server', self.root / 'objects', '--address', '127.0.0.1:9000', '--console-address', '127.0.0.1:9001'], port=9000)
        self.wait_http('minio', 'http://127.0.0.1:9000/minio/health/live')
        if self.enable_ai:
            self.start('ollama', [tools / 'bin/ollama', 'serve'], port=11434)
            self.wait_http('ollama', 'http://127.0.0.1:11434/api/tags')
            self.run([tools / 'bin/ollama', 'pull', 'qwen2.5:1.5b'], 'llm-model-download', timeout=1800)

    def start_apps(self):
        for name, (_, port) in self.app_services().items():
            env = dict(self.env, UBUNTUCARE_COLAB_SERVICE=name)
            self.start(name, [self.python, '-m', 'uvicorn', 'scripts.colab.asgi:create_app', '--factory', '--host', '127.0.0.1', '--port', str(port), '--workers', '1'], env=env, port=port)
            health_path = '/api/v1/rag/health' if name == 'rag' else '/health'
            predicate = (lambda data: data.get('status') == 'healthy' and data.get('components', {}).get('qdrant', {}).get('status') == 'healthy' and bool(data.get('components', {}).get('embeddings', {}).get('models')) and all(v == 'healthy' for v in data['components']['embeddings']['models'].values())) if name == 'rag' else (lambda data: data.get('status') == 'healthy')
            self.wait_http(name, f'http://127.0.0.1:{port}{health_path}', timeout=900 if name in {'rag', 'asr'} else 180, healthy=predicate)
        self.start('gateway', [self.python, '-m', 'uvicorn', 'scripts.colab.asgi:create_app', '--factory', '--host', '127.0.0.1', '--port', '8000'],
                   env=dict(self.env, UBUNTUCARE_COLAB_SERVICE='gateway'), port=8000)
        self.wait_http('gateway', 'http://127.0.0.1:8000/health', healthy=lambda data: data.get('status') == 'healthy')
        self.start('worker', [self.python, '-m', 'celery', '-A', 'scripts.colab.tasks:celery_app', 'worker', '--pool=solo', '--concurrency=1', '--loglevel=INFO'])
        self.start('beat', [self.python, '-m', 'celery', '-A', 'scripts.colab.tasks:celery_app', 'beat', '--schedule', self.root / 'celerybeat-schedule', '--pidfile', self.root / 'celerybeat.pid'])
        self.run([self.python, '-m', 'celery', '-A', 'scripts.colab.tasks:celery_app', 'inspect', 'ping', '--timeout=15'], 'worker-readiness', timeout=45)
        self.start('frontend', ['node', 'node_modules/next/dist/bin/next', 'start', '-H', '127.0.0.1', '-p', '3000'], cwd=REPO / 'src/frontend/web', port=3000)
        self.wait_http('frontend', 'http://127.0.0.1:3000/login')
        self.verify_login('http://127.0.0.1:3000')

    def verify_login(self, origin):
        import requests
        for email in ('admin@ubuntucare.gov.zm', 'john.mwamba@uh.gov.zm'):
            response = requests.post(origin + '/api/v1/auth/login', json={'email': email, 'password': 'UbuntuCare2024!'}, timeout=45, allow_redirects=False)
            if response.status_code != 200:
                raise RuntimeError(f'Login verification failed for demo account: HTTP {response.status_code}. See gateway and keycloak logs.')
            token = response.json().get('access_token')
            if not token:
                raise RuntimeError('Login endpoint returned no access token.')
            profile = requests.get(origin + '/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token}, timeout=30, allow_redirects=False)
            if profile.status_code != 200:
                raise RuntimeError(f'Authenticated profile check failed: HTTP {profile.status_code}')
            print(f'Login verified: {email}', flush=True)

    def expose(self):
        # Do not publish a frontend whose demo accounts cannot authenticate.
        self.verify_login('http://127.0.0.1:3000')
        self.start('tunnel', [self.root / 'downloads/cloudflared', 'tunnel', '--no-autoupdate', '--url', 'http://127.0.0.1:3000'])
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            text = (self.logs / 'tunnel.log').read_text(errors='replace')
            match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', text)
            if match:
                self.frontend_url = match.group(0)
                self.wait_http('tunnel', self.frontend_url + '/login', timeout=120)
                self.verify_login(self.frontend_url)
                return self.frontend_url
            if self.processes['tunnel'].poll() is not None:
                raise RuntimeError('Tunnel exited; inspect logs/tunnel.log')
            time.sleep(2)
        raise RuntimeError('No temporary URL was issued; inspect logs/tunnel.log')

    def status(self):
        for name, process in self.processes.items():
            print(f'{name:18s} {"RUNNING" if process.poll() is None else "EXITED " + str(process.returncode)}')
        print('Health-only shells: laboratory, pharmacy, medical imaging. Starting them does not implement their missing APIs.')
        print('Scheduler runs registered tasks only; unfinished production task names are not enqueued in Colab.')
        print('External SMS/email/WhatsApp providers need separate credentials. No real messages are sent by startup checks.')
        print('AI services:', 'enabled' if self.enable_ai else 'SKIPPED (Ollama, agents, ASR, TTS, RAG, Qdrant, Neo4j)')
        print('Colab excludes production ELK/Grafana/Prometheus/Portainer/Nginx/Weaviate.')

    def stop(self):
        for name, process in reversed(list(self.processes.items())):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
                print(f'Stopped {name}')
        self.frontend_url = None
        print('Native demo stopped; data retained until Colab deletes the runtime.')
