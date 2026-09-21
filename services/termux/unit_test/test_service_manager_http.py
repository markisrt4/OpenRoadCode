# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Authentication and request tests for the Termux runit HTTP control plane."""

from http.client import HTTPConnection
import json
import threading
import unittest
from unittest.mock import Mock

from services.common.service_manager_pairing import ServiceManagerPairing
from services.common.service_manager_browser_pairing import ServiceManagerBrowserPairing
from services.termux.service_manager import ServiceStatus
from services.termux.service_manager_http import ServiceManagerHandler, ThreadingHTTPServer


class ServiceManagerHttpRequestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = Mock()
        self.manager.all_status.return_value = (
            ServiceStatus("openroadcode-navigation", "running", "run: openroadcode-navigation"),
        )
        self.manager.start.return_value = self.manager.all_status.return_value[0]
        self.manager.stop.return_value = ServiceStatus(
            "openroadcode-navigation", "stopped", "down: openroadcode-navigation"
        )
        self.manager.restart.return_value = self.manager.all_status.return_value[0]
        self.manager.start_core.return_value = self.manager.all_status.return_value
        self.manager.stop_core.return_value = self.manager.all_status.return_value

        ServiceManagerHandler.manager = self.manager
        ServiceManagerHandler.auth_token = "secret"
        ServiceManagerHandler.pairing = ServiceManagerPairing()
        ServiceManagerHandler.browser_pairing = ServiceManagerBrowserPairing(ServiceManagerHandler.pairing)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ServiceManagerHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)
        ServiceManagerHandler.auth_token = None

    def request(self, method: str, path: str, token: str | None = "secret", body=None, form=None, pairing_token=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if pairing_token is not None:
            headers["X-OpenRoadCode-Pairing-Token"] = pairing_token
        connection = HTTPConnection(self.host, self.port, timeout=2.0)
        try:
            encoded = None
            if form is not None:
                from urllib.parse import urlencode
                encoded = urlencode(form)
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            elif body is not None:
                encoded = json.dumps(body)
                headers["Content-Type"] = "application/json"
            connection.request(method, path, body=encoded, headers=headers)
            response = connection.getresponse()
            raw = response.read().decode("utf-8")
            content_type = response.getheader("Content-Type", "")
            payload = json.loads(raw) if "application/json" in content_type else raw
            return response.status, payload
        finally:
            connection.close()

    def test_loopback_service_status_does_not_require_token(self) -> None:
        status, payload = self.request("GET", "/services", token=None)
        self.assertEqual(status, 200)
        self.assertEqual(payload["services"][0]["name"], "openroadcode-navigation")

    def test_loopback_service_action_does_not_require_token(self) -> None:
        status, payload = self.request(
            "POST", "/services/openroadcode-navigation/restart", token=None
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["services"][0]["state"], "running")
        self.manager.restart.assert_called_once_with("openroadcode-navigation")

    def test_valid_token_returns_service_status(self) -> None:
        status, payload = self.request("GET", "/services")
        self.assertEqual(status, 200)
        self.assertEqual(payload["services"][0]["name"], "openroadcode-navigation")
        self.manager.all_status.assert_called_once_with()

    def test_valid_token_allows_service_action(self) -> None:
        status, payload = self.request("POST", "/services/openroadcode-navigation/restart")
        self.assertEqual(status, 200)
        self.assertEqual(payload["services"][0]["state"], "running")
        self.manager.restart.assert_called_once_with("openroadcode-navigation")


    def test_browser_pairing_starts_without_admin_token(self) -> None:
        status, payload = self.request(
            "POST", "/pairing/browser/start", token=None,
            body={"client_name": "Test Android"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["session_id"])
        self.assertTrue(payload["poll_token"])
        self.assertNotIn(payload["poll_token"], payload["approval_url"])
        self.assertIn("/pairing/browser/approve/", payload["approval_url"])

    def test_same_device_browser_pairing_does_not_require_admin_token(self) -> None:
        _, started = self.request(
            "POST", "/pairing/browser/start", token=None,
            body={"client_name": "Test Android"},
        )
        status, approved = self.request(
            "POST",
            f"/pairing/browser/approve/{started['session_id']}",
            token=None,
        )
        self.assertEqual(status, 200)
        self.assertIn("Device approved", approved)

    def test_browser_pairing_status_requires_poll_token(self) -> None:
        _, started = self.request(
            "POST", "/pairing/browser/start", token=None,
            body={"client_name": "Test Android"},
        )
        status, response = self.request(
            "GET", f"/pairing/browser/status/{started['session_id']}", token=None
        )
        self.assertEqual(status, 401)
        self.assertEqual(response, {"error": "unauthorized"})

    def test_browser_pairing_issues_credentials_once_after_approval(self) -> None:
        _, started = self.request(
            "POST", "/pairing/browser/start", token=None,
            body={"client_name": "Test Android"},
        )
        from urllib.parse import parse_qs, urlsplit
        approval_token = parse_qs(urlsplit(started["approval_url"]).query)["token"][0]
        status, approved = self.request(
            "POST",
            f"/pairing/browser/approve/{started['session_id']}",
            token=None,
            form={"approval_token": approval_token},
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

    def test_pairing_start_requires_authentication(self) -> None:
        status, payload = self.request("POST", "/pairing/start", token=None)
        self.assertEqual(status, 401)
        self.assertEqual(payload, {"error": "unauthorized"})

    def test_pairing_start_and_exchange_issue_working_client_token(self) -> None:
        status, payload = self.request("POST", "/pairing/start")
        self.assertEqual(status, 200)
        pin = payload["pin"]
        self.assertEqual(len(pin), 6)
        self.assertTrue(pin.isdigit())
        self.assertIn("expires_at", payload)

        status, paired = self.request(
            "POST", "/pair", token=None,
            body={"pin": pin, "client_name": "Test phone"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(paired["client_id"])
        self.assertTrue(paired["access_token"])

        status, services = self.request(
            "GET", "/services", token=paired["access_token"]
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            services["services"][0]["name"], "openroadcode-navigation"
        )

    def test_paired_client_cannot_start_another_pairing(self) -> None:
        _, started = self.request("POST", "/pairing/start")
        _, paired = self.request(
            "POST", "/pair", token=None,
            body={"pin": started["pin"], "client_name": "Test phone"},
        )
        status, payload = self.request(
            "POST", "/pairing/start", token=paired["access_token"]
        )
        self.assertEqual(status, 401)
        self.assertEqual(payload, {"error": "unauthorized"})


if __name__ == "__main__":
    unittest.main()
