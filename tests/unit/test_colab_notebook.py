"""Offline execution regressions for the Colab smoke test (stdlib only).

HTTP responses are contract fixtures, not proof that a live deployment is healthy.
"""
import ast
import contextlib
import io
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch

NOTEBOOK = Path(__file__).resolve().parents[2] / "docs/colab/UbuntuCare_Online_Smoke_Test.ipynb"
CELLS = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]


def source(index):
    return "".join(CELLS[index]["source"])


class Response:
    def __init__(self, data=None, status=200):
        self.status_code = status
        self.data = data

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class Session:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith('/auth/login'):
            return Response({'access_token': 'fixture-token'})
        return Response({'id': '00000000-0000-4000-8000-000000000002'}, 201)

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith('/hospital/departments'):
            return Response([{'name': name, 'id': '00000000-0000-4000-8000-000000000003'} for name in ['General', 'Eye', 'Dental', 'Other']])
        if url.endswith('/patient-flow/destinations'):
            return Response({'service_points': [{'code': name} for name in ['general', 'eye', 'dental']]})
        return Response({'items': [], 'total': 0})

    def close(self):
        pass


class NotebookTests(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.requests = types.SimpleNamespace(Session=lambda: self.session, get=lambda *a, **k: Response(status=404))
        self.scope = {'requests': self.requests}
        self.output = io.StringIO()

    def run_cell(self, index, text=None):
        with contextlib.redirect_stdout(self.output):
            exec(compile(text or source(index), f'notebook cell {index}', 'exec'), self.scope)

    def setup_remote(self):
        self.run_cell(3, source(3).replace("LAUNCH_MODE = 'auto'", "LAUNCH_MODE = 'remote'"))

    def login(self, url='https://demo.example.test'):
        self.scope['REMOTE_FRONTEND_URL'] = url
        with patch.dict('sys.modules', {'requests': self.requests}), patch('builtins.input', side_effect=['', 'tester@example.test']), patch('getpass.getpass', return_value='fixture-secret'):
            self.run_cell(7)

    def test_all_python_cells_parse(self):
        for index, cell in enumerate(CELLS):
            if cell['cell_type'] == 'code':
                ast.parse('\n'.join(line for line in source(index).splitlines() if not line.startswith('%')), filename=f'cell {index}')

    def test_remote_run_all_never_installs_or_starts_containers(self):
        with patch('subprocess.run', side_effect=AssertionError('Unexpected process')), patch('subprocess.Popen', side_effect=AssertionError('Unexpected process')):
            self.setup_remote()
            # Stale local state must not select a local URL or password.
            self.scope.update(FRONTEND_URL='https://stale.example.test', DEMO_LOGIN_PASSWORD='stale', DEMO_LOGIN_EMAIL='stale')
            for index in [4, 5, 6]:
                self.run_cell(index)
            self.login()
            for index in [9, 11, 13, 15]:
                self.run_cell(index)
        self.assertEqual(self.scope['BASE_URL'], 'https://demo.example.test')
        self.assertEqual(len([url for url, _ in self.session.calls if url.endswith('/auth/login')]), 1)
        self.assertEqual(len([url for url, _ in self.session.calls if not url.endswith('/auth/login') and 'json' in _]), 0)
        for _, kwargs in self.session.calls:
            self.assertFalse(kwargs['allow_redirects'])
        self.assertNotIn('fixture-secret', self.output.getvalue())
        self.assertNotIn('fixture-token', self.output.getvalue())

    def test_cgroup_v1_v2_and_writable(self):
        self.setup_remote()
        check = self.scope['cgroup_mount_is_read_only']
        self.assertTrue(check('1 2 0:1 / /sys/fs/cgroup ro,nosuid - cgroup2 cgroup rw'))
        self.assertTrue(check('1 2 0:1 / /sys/fs/cgroup/memory ro - cgroup memory rw'))
        self.assertFalse(check('1 2 0:1 / /sys/fs/cgroup rw - cgroup2 cgroup rw'))
        self.assertFalse(check('malformed'))

    def test_restricted_auto_mode_skips_clone(self):
        preflight = source(3).split('if LAUNCH_MODE not in')[0]
        self.run_cell(3, preflight)
        self.scope['cgroup_mount_is_read_only'] = lambda: True
        with patch('subprocess.run', side_effect=AssertionError('Unexpected process')):
            self.run_cell(3, 'if LAUNCH_MODE not in' + source(3).split('if LAUNCH_MODE not in', 1)[1])
        self.assertFalse(self.scope['LOCAL_LAUNCH'])

    def test_reject_unsafe_origins_before_login(self):
        self.setup_remote()
        for url in ['http://demo.example.test', 'https://user:pass@example.test', 'https://example.test/api/v1', 'https://example.test?x=1', 'https://localhost']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.login(url)
        self.assertEqual(self.session.calls, [])

    def test_health_request_has_no_login_session(self):
        self.setup_remote()
        self.scope.update(BASE_URL='https://demo.example.test', LOCAL_LAUNCH=True)
        with patch.object(self.requests, 'get', return_value=Response({'status': 'healthy'})) as get:
            self.run_cell(9)
        self.assertEqual(get.call_args.args[0], 'http://127.0.0.1:8000/health')
        self.assertNotIn('headers', get.call_args.kwargs)

    def test_degraded_health_fails(self):
        self.setup_remote()
        self.scope['BASE_URL'] = 'https://demo.example.test'
        with patch.object(self.requests, 'get', return_value=Response({'status': 'degraded'})), self.assertRaises(RuntimeError):
            self.run_cell(9)

    def test_local_startup_rerun_preserves_credentials_and_project(self):
        import tempfile
        self.setup_remote()
        with tempfile.TemporaryDirectory() as directory:
            self.scope.update(LOCAL_LAUNCH=True, WORK_DIR=Path(directory), REPO_DIR=Path(directory), COMPOSE_CMD=['docker', 'compose'])
            result = types.SimpleNamespace(returncode=0, stdout='ready', stderr='')
            with patch('subprocess.run', return_value=result):
                self.run_cell(5)
                self.assertEqual(self.scope['DEMO_LOGIN_PASSWORD'], 'UbuntuCare2024!')
                self.assertIn('KEYCLOAK_DEMO_USER_PASSWORD=UbuntuCare2024!', self.scope['COLAB_ENV_FILE'].read_text())
                self.assertNotEqual(self.scope['env']['KEYCLOAK_ADMIN_PASSWORD'], 'UbuntuCare2024!')
                original = (self.scope['COLAB_PROJECT'], self.scope['DEMO_LOGIN_PASSWORD'], self.scope['COLAB_ENV_FILE'].read_text())
                self.run_cell(5)
            self.assertEqual(original, (self.scope['COLAB_PROJECT'], self.scope['DEMO_LOGIN_PASSWORD'], self.scope['COLAB_ENV_FILE'].read_text()))
            self.assertNotIn(self.scope['DEMO_LOGIN_PASSWORD'], self.output.getvalue())

    def test_cleanup_retains_volumes_and_reports_failure(self):
        self.setup_remote()
        self.scope.update(STOP_DEMO=True, COMPOSE=['docker', 'compose'], REPO_DIR=Path('.'))
        with patch('subprocess.run') as run:
            self.run_cell(15)
        self.assertNotIn('--volumes', run.call_args.args[0])
        self.assertTrue(run.call_args.kwargs['check'])

    def test_temporary_url_is_displayed_as_clickable_link(self):
        self.setup_remote()
        rendered = []
        display_module = types.ModuleType('IPython.display')
        display_module.HTML = lambda html: html
        display_module.display = rendered.append
        with patch.dict('sys.modules', {'IPython.display': display_module}), contextlib.redirect_stdout(self.output):
            self.scope['show_frontend_url']('https://fixture.trycloudflare.com', temporary=True)
        self.assertIn('Your temporary frontend URL: https://fixture.trycloudflare.com', self.output.getvalue())
        self.assertIn('href="https://fixture.trycloudflare.com/login"', rendered[0])
        self.assertIn('noopener noreferrer', rendered[0])

    def test_remote_url_is_displayed_before_authentication(self):
        self.setup_remote()
        self.login()
        output = self.output.getvalue()
        self.assertLess(output.index('Your connected frontend URL:'), output.index('POST /auth/login:'))
        self.assertIn('https://demo.example.test/login', output)

    def test_explicit_synthetic_write_flow(self):
        self.setup_remote()
        self.login()
        self.run_cell(11)
        self.scope['RUN_WRITE_TESTS'] = True
        self.run_cell(13)
        writes = [url for url, kwargs in self.session.calls if 'json' in kwargs and not url.endswith('/auth/login')]
        self.assertEqual(len(writes), 3)


if __name__ == '__main__':
    unittest.main()
