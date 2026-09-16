# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Authentication and request tests for the Termux runit HTTP control plane."""

from http.client import HTTPConnection
import json
import threading
import unittest
from unittest.mock import Mock

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
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ServiceManagerHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)
        ServiceManagerHandler.auth_token = None

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

    def test_valid_token_allows_service_action(self) -> None:
        status, payload = self.request("POST", "/services/openroadcode-navigation/restart")
        self.assertEqual(status, 200)
        self.assertEqual(payload["services"][0]["state"], "running")
        self.manager.restart.assert_called_once_with("openroadcode-navigation")


if __name__ == "__main__":
    unittest.main()
