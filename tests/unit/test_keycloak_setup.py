"""Readiness checks for native and container Keycloak configurations."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('keycloak_setup_test', ROOT / 'scripts/setup/setup_keycloak.py')
setup = importlib.util.module_from_spec(spec)
with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'ENV_FILE': str(Path(directory) / 'missing.env')}):
    spec.loader.exec_module(setup)


class KeycloakReadinessTests(unittest.TestCase):
    def test_enabled_health_endpoint_is_used_directly(self):
        with patch.object(setup, 'http_request', return_value=(200, b'{"status":"UP"}')) as request, contextlib.redirect_stdout(io.StringIO()):
            setup.wait_for_keycloak()
        self.assertEqual(request.call_count, 1)
        self.assertTrue(request.call_args.args[1].endswith('/health/ready'))

    def test_disabled_health_endpoint_uses_valid_discovery(self):
        document = json.dumps({'issuer': 'http://localhost/realms/master', 'token_endpoint': 'http://localhost/token'}).encode()
        with patch.object(setup, 'http_request', side_effect=[(404, b''), (200, document)]) as request, contextlib.redirect_stdout(io.StringIO()):
            setup.wait_for_keycloak()
        self.assertEqual(request.call_count, 2)
        self.assertTrue(request.call_args.args[1].endswith('/realms/master/.well-known/openid-configuration'))

    def test_unhealthy_endpoint_does_not_fall_back(self):
        with patch.object(setup, 'http_request', return_value=(503, b'')) as request, patch.object(setup.time, 'time', side_effect=[0, 1, 121]), patch.object(setup.time, 'sleep'), self.assertRaises(setup.KeycloakSetupError):
            setup.wait_for_keycloak()
        self.assertEqual(request.call_count, 1)

    def test_html_discovery_does_not_mark_ready(self):
        with patch.object(setup, 'http_request', side_effect=[(404, b''), (200, b'<html>Not discovery</html>')]), patch.object(setup.time, 'time', side_effect=[0, 1, 121]), patch.object(setup.time, 'sleep'), self.assertRaises(setup.KeycloakSetupError):
            setup.wait_for_keycloak()


if __name__ == '__main__': unittest.main()
