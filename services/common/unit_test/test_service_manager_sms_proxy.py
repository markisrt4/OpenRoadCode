# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fail-closed SMS proxy contract tests."""

from __future__ import annotations

from io import BytesIO
import os
import unittest
from unittest.mock import patch

from services.common.service_manager_sms_proxy import serve_sms


class FakeHandler:
    def __init__(self, path="/sms/conversations", authorization=None, body=b""):
        self.path = path
        self.headers = {"Authorization": authorization} if authorization else {}
        self.headers["Content-Length"] = str(len(body))
        self.rfile = BytesIO(body)
        self.result = None

    def _json(self, status, payload):
        self.result = (status.value, payload)


class SmsProxyTest(unittest.TestCase):
    def test_unrelated_path_not_handled(self):
        handler = FakeHandler("/services")
        self.assertFalse(serve_sms(handler, "GET"))
        self.assertIsNone(handler.result)

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            handler = FakeHandler()
            self.assertTrue(serve_sms(handler, "GET"))
            self.assertEqual(handler.result[0], 503)

    def test_enabled_without_credentials_fails_closed(self):
        with patch.dict(os.environ, {"OPENROADCODE_SMS_ENABLED": "1"}, clear=True):
            handler = FakeHandler()
            serve_sms(handler, "GET")
            self.assertEqual(handler.result[0], 503)

    def test_localhost_cannot_bypass_sms_token(self):
        env = {"OPENROADCODE_SMS_ENABLED": "1", "OPENROADCODE_SMS_TOKEN": "client",
               "OPENROADCODE_ANDROID_SMS_TOKEN": "android"}
        with patch.dict(os.environ, env, clear=True):
            handler = FakeHandler()
            serve_sms(handler, "GET")
            self.assertEqual(handler.result[0], 401)

    def test_invalid_post_body_rejected_before_forwarding(self):
        env = {"OPENROADCODE_SMS_ENABLED": "1", "OPENROADCODE_SMS_TOKEN": "client",
               "OPENROADCODE_ANDROID_SMS_TOKEN": "android"}
        with patch.dict(os.environ, env, clear=True):
            handler = FakeHandler("/sms/send", "Bearer client", b"not json")
            serve_sms(handler, "POST")
            self.assertEqual(handler.result[0], 400)


if __name__ == "__main__":
    unittest.main()
