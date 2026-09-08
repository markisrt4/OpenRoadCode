# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Authentication and request tests for the Linux service-manager HTTP control plane."""

from http.client import HTTPConnection
import json
import subprocess
import threading
import unittest
from unittest.mock import Mock

from services.linux.systemd_service_manager import ServiceStatus
from services.linux.systemd_service_manager_http import (
    SystemdServiceManagerHandler,
    ThreadingHTTPServer,
    _authorized,
    _binding_allowed,
)


class SystemdServiceManagerHttpPolicyTest(unittest.TestCase):
    def test_no_token_allows_local_mode_requests(self) -> None:
        self.assertTrue(_authorized(None, None))

    def test_configured_token_requires_bearer_header(self) -> None:
        self.assertFalse(_authorized(None, "secret"))
        self.assertFalse(_authorized("secret", "secret"))

    def test_configured_token_accepts_exact_bearer_value(self) -> None:
        self.assertTrue(_authorized("Bearer secret", "secret"))

    def test_configured_token_rejects_wrong_bearer_value(self) -> None:
        self.assertFalse(_authorized("Bearer wrong", "secret"))

    def test_loopback_binding_does_not_require_token(self) -> None:
        self.assertTrue(_binding_allowed("127.0.0.1", None))
        self.assertTrue(_binding_allowed("localhost", None))
        self.assertTrue(_binding_allowed("::1", None))

    def test_remote_binding_requires_token(self) -> None:
        self.assertFalse(_binding_allowed("0.0.0.0", None))
        self.assertFalse(_binding_allowed("192.168.8.2", None))
        self.assertTrue(_binding_allowed("0.0.0.0", "secret"))


class SystemdServiceManagerHttpRequestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = Mock()
        self.manager.all_status.return_value = (
            ServiceStatus("openroadcode-navigation", "running", "active / running / enabled"),
        )
        self.manager.start.return_value = ServiceStatus(
            "openroadcode-navigation", "running", "active / running / enabled"
        )
        self.manager.stop.return_value = ServiceStatus(
            "openroadcode-navigation", "stopped", "inactive / dead / enabled"
        )
        self.manager.restart.return_value = ServiceStatus(
            "openroadcode-navigation", "running", "active / running / enabled"
        )
        self.manager.start_core.return_value = self.manager.all_status.return_value
        self.manager.stop_core.return_value = self.manager.all_status.return_value

        SystemdServiceManagerHandler.manager = self.manager
        SystemdServiceManagerHandler.auth_token = "secret"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), SystemdServiceManagerHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)
        SystemdServiceManagerHandler.auth_token = None

    def request(self, method: str, path: str, token: str | None = "secret"):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        connection = HTTPConnection(self.host, self.port, timeout=2.0)
        try:
            connection.request(method, path, headers=headers)
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload
        finally:
            connection.close()

    def test_missing_token_is_rejected(self) -> None:
        status, payload = self.request("GET", "/services", token=None)

        self.assertEqual(status, 401)
        self.assertEqual(payload, {"error": "unauthorized"})
        self.manager.all_status.assert_not_called()

    def test_wrong_token_is_rejected(self) -> None:
        status, payload = self.request("GET", "/services", token="wrong")

        self.assertEqual(status, 401)
        self.assertEqual(payload, {"error": "unauthorized"})

    def test_valid_token_returns_service_status(self) -> None:
        status, payload = self.request("GET", "/services")

        self.assertEqual(status, 200)
        self.assertEqual(payload["services"][0]["name"], "openroadcode-navigation")
        self.manager.all_status.assert_called_once_with()

    def test_allowed_service_action_is_forwarded(self) -> None:
        status, payload = self.request("POST", "/services/openroadcode-navigation/restart")

        self.assertEqual(status, 200)
        self.assertEqual(payload["services"][0]["state"], "running")
        self.manager.restart.assert_called_once_with("openroadcode-navigation")

    def test_invalid_service_name_returns_bad_request(self) -> None:
        self.manager.start.side_effect = ValueError("Unsupported OpenRoadCode service: ssh")

        status, payload = self.request("POST", "/services/ssh/start")

        self.assertEqual(status, 400)
        self.assertIn("Unsupported OpenRoadCode service", payload["error"])

    def test_systemctl_failure_returns_bad_request(self) -> None:
        self.manager.restart.side_effect = subprocess.CalledProcessError(1, ["systemctl"])

        status, payload = self.request("POST", "/services/openroadcode-navigation/restart")

        self.assertEqual(status, 400)
        self.assertIn("returned non-zero exit status", payload["error"])


if __name__ == "__main__":
    unittest.main()
