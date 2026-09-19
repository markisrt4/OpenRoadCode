# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Authentication and request tests for the Termux runit HTTP control plane."""

from http.client import HTTPConnection
import json
import threading
import unittest
from unittest.mock import Mock

from services.common.service_manager_pairing import ServiceManagerPairing
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
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ServiceManagerHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)
        ServiceManagerHandler.auth_token = None

    def request(self, method: str, path: str, token: str | None = "secret", body=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        connection = HTTPConnection(self.host, self.port, timeout=2.0)
        try:
            encoded = None
            if body is not None:
                encoded = json.dumps(body)
                headers["Content-Type"] = "application/json"
            connection.request(method, path, body=encoded, headers=headers)
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

    def test_valid_token_allows_service_action(self) -> None:
        status, payload = self.request("POST", "/services/openroadcode-navigation/restart")
        self.assertEqual(status, 200)
        self.assertEqual(payload["services"][0]["state"], "running")
        self.manager.restart.assert_called_once_with("openroadcode-navigation")


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
