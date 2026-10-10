# SPDX-License-Identifier: MIT
"""SMS proxy forwarding and authentication regression tests."""

from __future__ import annotations

from io import BytesIO
import json
import os
import unittest
from unittest.mock import patch

from services.common.service_manager_sms_proxy import serve_sms


class Handler:
    path = "/sms/conversations?limit=5"

    def __init__(self, authorization):
        self.headers = {"Authorization": authorization}
        self.rfile = BytesIO()
        self.result = None

    def _json(self, status, payload):
        self.result = (status.value, payload)


class Response:
    status = 200

    def getheader(self, name):
        return None

    def read(self, size):
        return b'{"conversations":[]}'


class Connection:
    calls = []

    def __init__(self, host, port, timeout):
        self.calls.append(("connect", host, port, timeout))

    def request(self, method, path, body=None, headers=None):
        self.calls.append(("request", method, path, body, headers))

    def getresponse(self):
        return Response()

    def close(self):
        self.calls.append(("close",))


class SmsForwardingTest(unittest.TestCase):
    def test_authorized_request_uses_android_token_and_registered_port(self):
        Connection.calls = []
        env = {
            "OPENROADCODE_SMS_ENABLED": "1",
            "OPENROADCODE_SMS_TOKEN": "external-secret",
            "OPENROADCODE_ANDROID_SMS_TOKEN": "internal-secret",
        }
        with patch.dict(os.environ, env, clear=True), patch(
            "services.common.service_manager_sms_proxy.HTTPConnection", Connection
        ):
            handler = Handler("Bearer external-secret")
            self.assertTrue(serve_sms(handler, "GET"))
        self.assertEqual(handler.result, (200, {"conversations": []}))
        self.assertEqual(Connection.calls[0], ("connect", "127.0.0.1", 8773, 3))
        request = Connection.calls[1]
        self.assertEqual(request[:3], ("request", "GET", "/sms/conversations?limit=5"))
        self.assertEqual(request[4]["Authorization"], "Bearer internal-secret")
        self.assertNotIn("external-secret", json.dumps(Connection.calls))

    def test_bad_client_token_never_contacts_android(self):
        Connection.calls = []
        env = {
            "OPENROADCODE_SMS_ENABLED": "1",
            "OPENROADCODE_SMS_TOKEN": "external-secret",
            "OPENROADCODE_ANDROID_SMS_TOKEN": "internal-secret",
        }
        with patch.dict(os.environ, env, clear=True), patch(
            "services.common.service_manager_sms_proxy.HTTPConnection", Connection
        ):
            handler = Handler("Bearer wrong")
            self.assertTrue(serve_sms(handler, "GET"))
        self.assertEqual(handler.result[0], 401)
        self.assertEqual(Connection.calls, [])


if __name__ == "__main__":
    unittest.main()
