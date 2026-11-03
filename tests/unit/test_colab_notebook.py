"""Offline tests for the Docker-free Colab launcher. Live runtime tests are separate."""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
CELLS = json.loads((ROOT / 'docs/colab/UbuntuCare_Online_Smoke_Test.ipynb').read_text(encoding='utf-8'))['cells']
spec = importlib.util.spec_from_file_location('native_runtime_test', ROOT / 'scripts/colab/native_runtime.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def source(i):
    return ''.join(CELLS[i]['source'])


class Response:
    status_code = 200
    def json(self):
        return {'access_token': 'fixture-token', 'items': [], 'total': 0}


class Session:
    def __init__(self): self.headers = {}
    def post(self, *args, **kwargs): return Response()
    def close(self): pass


class NotebookTests(unittest.TestCase):
    def setUp(self):
        self.scope = {'runtime': Mock(), 'requests': types.SimpleNamespace(Session=Session),
                      'DEMO_LOGIN_EMAIL': 'admin@ubuntucare.gov.zm', 'DEMO_DOCTOR_EMAIL': 'john.mwamba@uh.gov.zm',
                      'DEMO_LOGIN_PASSWORD': 'UbuntuCare2024!', 'HOSPITAL_ID': '00000000-0000-4000-8000-000000000001',
                      'show_frontend_url': Mock()}
        self.scope['runtime'].expose.return_value = 'https://fixture.trycloudflare.com'

    def cell(self, i):
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source(i), f'cell {i}', 'exec'), self.scope)

    def test_every_python_cell_parses(self):
        for i, c in enumerate(CELLS):
            if c['cell_type'] == 'code':
                ast.parse('\n'.join(line for line in source(i).splitlines() if not line.startswith('%')))

    def test_run_sequence_does_not_prompt_for_an_existing_url(self):
        with patch('builtins.input', side_effect=AssertionError('No URL prompts allowed')):
            for i in (5, 6, 7, 15): self.cell(i)
        runtime = self.scope['runtime']
        runtime.start_data.assert_called_once()
        runtime.start_apps.assert_called_once()
        self.assertEqual(self.scope['FRONTEND_URL'], 'https://fixture.trycloudflare.com')
        self.scope['show_frontend_url'].assert_called_once_with('https://fixture.trycloudflare.com', temporary=True)
        runtime.stop.assert_not_called()

    def test_failed_exposure_does_not_display_a_link(self):
        self.scope['runtime'].expose.side_effect = RuntimeError('Login failed')
        with self.assertRaises(RuntimeError): self.cell(6)
        self.scope['show_frontend_url'].assert_not_called()

    def test_rejects_local_windows_launch(self):
        with patch.object(native.sys, 'platform', 'win32'), self.assertRaises(RuntimeError): native.require_colab()

    def test_service_ports_are_unique(self):
        ports = [port for _, port in native.SERVICES.values()]
        self.assertEqual(len(ports), len(set(ports)))
        self.assertEqual(len(ports), 15)

    def test_wait_fails_immediately_when_process_exits(self):
        runtime = object.__new__(native.ColabRuntime)
        runtime.processes = {'gateway': Mock(poll=lambda: 1)}
        runtime.logs = Path('/content/logs')
        with self.assertRaisesRegex(RuntimeError, 'gateway exited'):
            runtime.wait_http('gateway', 'http://127.0.0.1:8000/health')

    def test_stop_only_terminates_owned_process_groups(self):
        runtime = object.__new__(native.ColabRuntime)
        owned = Mock(pid=1234, poll=lambda: None)
        exited = Mock(pid=4567, poll=lambda: 0)
        runtime.processes = {'owned': owned, 'exited': exited}
        with patch.object(native.os, 'killpg', create=True) as kill, contextlib.redirect_stdout(io.StringIO()): runtime.stop()
        kill.assert_called_once_with(1234, native.signal.SIGTERM)
        owned.wait.assert_called_once_with(timeout=20)
        exited.wait.assert_not_called()

    def test_service_entrypoints_have_required_os_import(self):
        for path in (ROOT / 'src/backend/services').glob('*/main.py'):
            text = path.read_text(encoding='utf-8-sig')
            if 'os.getenv(' in text:
                self.assertTrue(any(isinstance(n, ast.Import) and any(a.name == 'os' for a in n.names) for n in ast.parse(text).body), str(path))

    def test_migration_chain_includes_rag_vector_table(self):
        tree = ast.parse((ROOT / 'data/migrations/versions/013_rag_vector_schema.py').read_text(encoding='utf-8-sig'))
        assignments = {n.targets[0].id: n.value.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)}
        self.assertEqual(assignments['revision'], '013')
        self.assertEqual(assignments['down_revision'], '012')

    def test_all_native_asgi_commands_bind_to_loopback(self):
        text = (ROOT / 'scripts/colab/native_runtime.py').read_text(encoding='utf-8-sig')
        self.assertNotIn("'0.0.0.0'", text)
        self.assertNotIn("'docker'", text)
        self.assertNotIn('shell=True', text)

    def test_venv_uses_system_python_not_kernel_python(self):
        runtime = object.__new__(native.ColabRuntime)
        runtime.root = Path('/content/demo')
        runtime.env = {'PATH': '/usr/bin', 'PYTHONHOME': '/kernel', 'PYTHONPATH': '/kernel/modules'}
        runtime.run = Mock()
        with patch.object(native.Path, 'is_file', return_value=True), contextlib.redirect_stdout(io.StringIO()):
            runtime.create_python_environment()
        args, kwargs = runtime.run.call_args_list[0]
        self.assertEqual(args[0][0], Path('/usr/bin/python3'))
        self.assertNotIn('PYTHONHOME', kwargs['env'])
        self.assertNotIn('PYTHONPATH', kwargs['env'])
        self.assertEqual(runtime.python, Path('/content/demo/venv-system/bin/python'))
        self.assertTrue(runtime.env['PATH'].startswith(str(runtime.python.parent)))

    def test_venv_fallback_handles_missing_ensurepip(self):
        runtime = object.__new__(native.ColabRuntime)
        runtime.root = Path('/content/demo')
        runtime.env = {'PATH': '/usr/bin'}
        runtime.run = Mock(side_effect=[RuntimeError('ensurepip unavailable'), None, None, None])
        with patch.object(native.Path, 'is_file', return_value=True), contextlib.redirect_stdout(io.StringIO()):
            runtime.create_python_environment()
        commands = [call.args[0] for call in runtime.run.call_args_list]
        self.assertIn('virtualenv==20.29.3', commands[1])
        self.assertEqual(commands[2][1:4], ['-m', 'virtualenv', '--python'])
        self.assertEqual(runtime.python, Path('/content/demo/venv-fallback/bin/python'))

    def test_environment_failure_does_not_report_success(self):
        runtime = object.__new__(native.ColabRuntime)
        runtime.root = Path('/content/demo')
        runtime.env = {'PATH': '/usr/bin'}
        runtime.run = Mock(side_effect=RuntimeError('environment creation failed'))
        output = io.StringIO()
        with patch.object(native.Path, 'is_file', return_value=True), contextlib.redirect_stdout(output), self.assertRaises(RuntimeError):
            runtime.create_python_environment()
        self.assertNotIn('environment ready', output.getvalue())

    def test_core_install_skips_all_ai_downloads_and_dependencies(self):
        for enable_ai in (False, True):
            with self.subTest(enable_ai=enable_ai), tempfile.TemporaryDirectory() as directory, patch.object(native, 'require_colab'):
                runtime = native.ColabRuntime(root=directory, enable_ai=enable_ai)
                runtime.run = Mock()
                runtime.create_python_environment = Mock()
                runtime.configure_hosts = Mock()
                def download(url, destination):
                    destination.write_bytes(b'fixture')
                    return destination
                def unpack(archive, destination):
                    destination.mkdir(parents=True, exist_ok=True)
                with patch.object(native, 'available_memory_gib', return_value=16), patch.object(native.shutil, 'disk_usage', return_value=types.SimpleNamespace(free=100 * 1024**3)), patch.object(native, 'fetch', side_effect=download) as fetch, patch.object(native, 'extract', side_effect=unpack), contextlib.redirect_stdout(io.StringIO()):
                    runtime.install()
                steps = [call.args[1] for call in runtime.run.call_args_list]
                self.assertEqual('torch-install' in steps, enable_ai)
                self.assertEqual('python-ai-dependencies' in steps, enable_ai)
                self.assertEqual('apt-ai-install' in steps, enable_ai)
                for name in ('agents', 'asr', 'tts', 'rag'):
                    self.assertEqual('import-' + name in steps, enable_ai)
                urls = [call.args[0] for call in fetch.call_args_list]
                for name in ('qdrant', 'ollama', 'neo4j'):
                    self.assertEqual(native.DOWNLOADS[name][0] in urls, enable_ai)
                npm_install = next(call.args[0] for call in runtime.run.call_args_list if call.args[1] == 'frontend-dependencies')
                self.assertIn('--include=dev', npm_install)
                self.assertIn('frontend-build-tools', steps)
                self.assertIn('worker-dependencies-check', steps)
                self.assertLess(steps.index('worker-dependencies-check'), steps.index('frontend-build'))
                self.assertIn('frontend-build', steps)
                self.assertIn('import-emr', steps)

    def test_core_startup_keeps_auth_and_frontend_without_ai(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(native, 'require_colab'):
            runtime = native.ColabRuntime(root=directory)
            runtime.start = Mock()
            runtime.wait_http = Mock()
            runtime.run = Mock()
            runtime.verify_login = Mock()
            with patch.object(native.Path, 'iterdir', return_value=iter([Path('/usr/lib/postgresql/15')])), patch.object(native.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)), contextlib.redirect_stdout(io.StringIO()):
                runtime.start_data()
                runtime.start_apps()
            started = [call.args[0] for call in runtime.start.call_args_list]
            for name in ('postgres', 'redis', 'keycloak', 'emr', 'gateway', 'frontend'):
                self.assertIn(name, started)
            for name in ('ollama', 'agents', 'asr', 'tts', 'rag', 'qdrant', 'neo4j'):
                self.assertNotIn(name, started)
            setup_call = next(call for call in runtime.run.call_args_list if call.args[1] == 'database-users')
            command = setup_call.args[0]
            postgres_command = next(call.args[1] for call in runtime.start.call_args_list if call.args[0] == 'postgres')
            self.assertEqual(command[command.index('-p') + 1], postgres_command[postgres_command.index('-p') + 1])
            self.assertEqual(command[command.index('-h') + 1], runtime.root / 'postgres')
            self.assertEqual(command[command.index('-U') + 1], 'postgres')
            self.assertEqual(command[command.index('-d') + 1], 'postgres')
            self.assertIn('-X', command)
            self.assertNotIn(runtime.private['db_password'], ' '.join(map(str, command)))
            runtime.verify_login.assert_called_once_with('http://127.0.0.1:3000')
            readiness = next(call for call in runtime.run.call_args_list if call.args[1] == 'worker-readiness')
            script = readiness.args[0][-1]
            result = Mock()
            result.get.return_value = {'status': 'ok'}
            app = Mock()
            app.send_task.return_value = result
            module = types.ModuleType('scripts.colab.tasks')
            module.celery_app = app
            with patch.dict('sys.modules', {'scripts.colab.tasks': module}), contextlib.redirect_stdout(io.StringIO()):
                exec(script, {})
                app.send_task.assert_called_once_with('core.health_check')
                result.get.assert_called_once_with(timeout=90)
                result.forget.assert_called_once()
                result.get.return_value = {'status': 'failed'}
                with self.assertRaises(AssertionError):
                    exec(script, {})
            self.assertEqual(runtime.env['UBUNTUCARE_COLAB_ENABLE_AI'], '0')
            self.assertNotIn('llm-model-download', [call.args[1] for call in runtime.run.call_args_list])

    def test_disabled_ai_routes_report_503_and_leave_core_routes_available(self):
        import asyncio
        from unittest.mock import AsyncMock
        import asgi
        middleware = []
        app = types.SimpleNamespace(middleware=lambda _: lambda fn: middleware.append(fn), api_route=lambda *a, **k: lambda fn: fn)
        registry = types.SimpleNamespace(_services={})
        response_module = types.ModuleType('fastapi.responses')
        response_module.JSONResponse = lambda **kwargs: kwargs
        gateway_module = types.ModuleType('src.backend.api_gateway.main')
        gateway_module.app = app
        routes_module = types.ModuleType('src.backend.api_gateway.routes')
        routes_module.registry = registry
        routes_module.build_proxy_handler = Mock()
        with patch.dict('sys.modules', {'fastapi.responses': response_module, 'src.backend.api_gateway.main': gateway_module, 'src.backend.api_gateway.routes': routes_module}), patch.dict(native.os.environ, {'UBUNTUCARE_COLAB_SERVICE': 'gateway', 'UBUNTUCARE_COLAB_ENABLE_AI': '0'}):
            asgi.create_app()
        next_handler = AsyncMock(return_value='core-response')
        for path in ('/api/v1/agents/chat', '/api/v1/asr/transcribe', '/api/v1/tts', '/v2/rag/search'):
            response = asyncio.run(middleware[0](types.SimpleNamespace(url=types.SimpleNamespace(path=path)), next_handler))
            self.assertEqual(response['status_code'], 503)
        next_handler.assert_not_awaited()
        response = asyncio.run(middleware[0](types.SimpleNamespace(url=types.SimpleNamespace(path='/api/v1/auth/login')), next_handler))
        self.assertEqual(response, 'core-response')
        self.assertEqual(registry._services['agents'], [])

    def test_frontend_failure_shows_redacted_build_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(native, 'require_colab'):
            runtime = native.ColabRuntime(root=directory)
            secret = runtime.private['secret_key']
            def fail(args, **kwargs):
                kwargs['stdout'].write('Build failed: sample error ' + secret + ' https://user:password@example.test/package')
                return types.SimpleNamespace(returncode=1)
            output = io.StringIO()
            with patch.object(native.subprocess, 'run', side_effect=fail), contextlib.redirect_stdout(output), self.assertRaises(RuntimeError):
                runtime.run(['npm', 'run', 'build'], 'frontend-build')
            self.assertIn('sample error', output.getvalue())
            self.assertNotIn(secret, output.getvalue())
            self.assertNotIn('user:password', output.getvalue())

    def test_frontend_libraries_are_not_ignored(self):
        import subprocess
        paths = [str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / 'src/frontend/web/src/lib').glob('*.ts')]
        self.assertTrue(paths)
        result = subprocess.run(['git', 'check-ignore', '--no-index', *paths], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_archive_rejects_traversal(self):
        import tarfile
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'bad.tar'
            with tarfile.open(archive, 'w') as bundle:
                item = tarfile.TarInfo('../escape.txt')
                item.size = 1
                bundle.addfile(item, io.BytesIO(b'x'))
            with self.assertRaises(tarfile.FilterError): native.extract(archive, Path(directory) / 'output')
            self.assertFalse((Path(directory) / 'escape.txt').exists())


if __name__ == '__main__': unittest.main()
