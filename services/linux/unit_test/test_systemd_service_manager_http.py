# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Authentication and request tests for the Linux service-manager HTTP control plane."""

from http.client import HTTPConnection
import json
import subprocess
import threading
import unittest
from unittest.mock import Mock, patch

from services.common.service_manager_pairing import ServiceManagerPairing
from services.common.service_manager_browser_pairing import ServiceManagerBrowserPairing
from services.linux.systemd_service_manager import ServiceStatus
from services.linux.systemd_service_manager_http import (
    SystemdServiceManagerHandler,
    ThreadingHTTPServer,
    _authorized,
    _binding_allowed,
)
from services.common.service_manager_auth import same_device_request


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

    def test_same_device_request_accepts_local_interface_connection(self) -> None:
        self.assertTrue(same_device_request("192.168.0.217", "192.168.0.217"))
        self.assertTrue(same_device_request("127.0.0.1", "127.0.0.1"))

    def test_same_device_request_rejects_remote_client(self) -> None:
        self.assertFalse(same_device_request("192.168.0.50", "192.168.0.217"))

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
        SystemdServiceManagerHandler.pairing = ServiceManagerPairing()
        SystemdServiceManagerHandler.browser_pairing = ServiceManagerBrowserPairing(SystemdServiceManagerHandler.pairing)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), SystemdServiceManagerHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)
        SystemdServiceManagerHandler.auth_token = None
        SystemdServiceManagerHandler.pairing = ServiceManagerPairing()

    def request(
        self,
        method: str,
        path: str,
        token: str | None = "secret",
        payload: dict[str, object] | None = None,
        form: dict[str, str] | None = None,
        pairing_token: str | None = None,
    ):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if pairing_token is not None:
            headers["X-OpenRoadCode-Pairing-Token"] = pairing_token
        body = None
        if form is not None:
            from urllib.parse import urlencode
            body = urlencode(form)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif payload is not None:
            body = json.dumps(payload)
            headers["Content-Type"] = "application/json"
        connection = HTTPConnection(self.host, self.port, timeout=2.0)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read().decode("utf-8")
            content_type = response.getheader("Content-Type", "")
            response_payload = json.loads(raw) if "application/json" in content_type else raw
            return response.status, response_payload
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

    def test_browser_pairing_starts_without_admin_token(self) -> None:
        status, payload = self.request(
            "POST", "/pairing/browser/start", token=None,
            payload={"client_name": "Test Android"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["session_id"])
        self.assertTrue(payload["poll_token"])
        self.assertNotIn(payload["poll_token"], payload["approval_url"])
        self.assertIn("/pairing/browser/approve/", payload["approval_url"])

    def test_same_device_browser_pairing_does_not_require_admin_token(self) -> None:
        _, started = self.request(
            "POST", "/pairing/browser/start", token=None,
            payload={"client_name": "Test Android"},
        )
        status, approved = self.request(
            "POST",
            f"/pairing/browser/approve/{started['session_id']}",
            token=None,
        )
        self.assertEqual(status, 200)
        self.assertIn("Device approved", approved)

    def test_remote_browser_pairing_uses_short_lived_pin_not_admin_token(self) -> None:
        with patch(
            "services.common.service_manager_browser_pairing.secrets.randbelow",
            return_value=123456,
        ), patch.object(
            SystemdServiceManagerHandler, "_same_device_request", return_value=False
        ):
            _, started = self.request(
                "POST", "/pairing/browser/start", token=None,
                payload={"client_name": "Test Android"},
            )
            status, page = self.request(
                "GET", f"/pairing/browser/approve/{started['session_id']}", token=None
            )
            self.assertEqual(status, 200)
            self.assertIn("short-lived pairing PIN", page)
            self.assertNotIn("administrator token", page)

            status, rejected = self.request(
                "POST",
                f"/pairing/browser/approve/{started['session_id']}",
                token=None,
                form={"approval_pin": "000000"},
            )
            self.assertEqual(status, 401)
            self.assertIn("Pairing PIN was not accepted", rejected)

            status, approved = self.request(
                "POST",
                f"/pairing/browser/approve/{started['session_id']}",
                token=None,
                form={"approval_pin": "123456"},
            )
            self.assertEqual(status, 200)
            self.assertIn("Device approved", approved)

    def test_browser_pairing_status_requires_poll_token(self) -> None:
        _, started = self.request(
            "POST", "/pairing/browser/start", token=None,
            payload={"client_name": "Test Android"},
        )
        status, response = self.request(
            "GET", f"/pairing/browser/status/{started['session_id']}", token=None
        )
        self.assertEqual(status, 401)
        self.assertEqual(response, {"error": "unauthorized"})

    def test_browser_pairing_issues_credentials_once_after_approval(self) -> None:
        _, started = self.request(
            "POST", "/pairing/browser/start", token=None,
            payload={"client_name": "Test Android"},
        )
        status, approved = self.request(
            "POST",
            f"/pairing/browser/approve/{started['session_id']}",
            token=None,
            form={"admin_token": "secret"},
        )
        self.assertEqual(status, 200)
        self.assertIn("Device approved", approved)

        status, completed = self.request(
            "GET", f"/pairing/browser/status/{started['session_id']}", token=None,
            pairing_token=started["poll_token"],
        )
        self.assertEqual(status, 200)
        self.assertEqual(completed["status"], "approved")
        self.assertTrue(completed["client_id"])
        self.assertTrue(completed["access_token"])

        status, consumed = self.request(
            "GET", f"/pairing/browser/status/{started['session_id']}", token=None,
            pairing_token=started["poll_token"],
        )
        self.assertEqual(status, 410)
        self.assertEqual(consumed, {"error": "pairing session already consumed"})

    def test_pairing_start_requires_bootstrap_token(self) -> None:
        status, payload = self.request("POST", "/pairing/start", token=None)

        self.assertEqual(status, 401)
        self.assertEqual(payload, {"error": "unauthorized"})

    def test_pairing_exchange_authorizes_new_client(self) -> None:
        status, started = self.request("POST", "/pairing/start")
        self.assertEqual(status, 200)
        self.assertRegex(started["pin"], r"^\d{6}$")

        status, paired = self.request(
            "POST",
            "/pair",
            token=None,
            payload={"pin": started["pin"], "client_name": "Test Android"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(paired["client_id"])
        self.assertTrue(paired["access_token"])

        status, services = self.request("GET", "/services", token=paired["access_token"])
        self.assertEqual(status, 200)
        self.assertEqual(services["services"][0]["name"], "openroadcode-navigation")

    def test_paired_client_cannot_start_another_pairing(self) -> None:
        _, started = self.request("POST", "/pairing/start")
        _, paired = self.request(
            "POST",
            "/pair",
            token=None,
            payload={"pin": started["pin"], "client_name": "Test Android"},
        )

        status, payload = self.request(
            "POST", "/pairing/start", token=paired["access_token"]
        )
        self.assertEqual(status, 401)
        self.assertEqual(payload, {"error": "unauthorized"})


if __name__ == "__main__":
    unittest.main()
