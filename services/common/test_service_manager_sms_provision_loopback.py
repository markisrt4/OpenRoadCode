# SPDX-License-Identifier: MIT
"""Focused loopback restriction tests for SMS credential provisioning."""
import os
import unittest
from unittest.mock import patch
from services.common.service_manager_sms_provision import serve_sms_provision


class Handler:
    path = "/sms/provision"
    headers = {"Authorization": "Bearer " + "a" * 40}
    def __init__(self, address):
        self.client_address = (address, 10000)
        self.result = None
    def _json(self, status, body):
        self.result = (int(status), body)


class ProvisionLoopbackTest(unittest.TestCase):
    def test_remote_rejected_even_with_valid_token(self):
        with patch.dict(os.environ, {"OPENROADCODE_SMS_PROVISION_TOKEN": "a" * 40}):
            handler = Handler("192.168.1.20")
            self.assertTrue(serve_sms_provision(handler, "GET"))
            self.assertEqual(handler.result, (403, {"error": "forbidden"}))

    def test_loopback_still_requires_authorization(self):
        with patch.dict(os.environ, {"OPENROADCODE_SMS_PROVISION_TOKEN": "b" * 40}):
            handler = Handler("127.0.0.1")
            self.assertTrue(serve_sms_provision(handler, "GET"))
            self.assertEqual(handler.result, (401, {"error": "unauthorized"}))


if __name__ == "__main__":
    unittest.main()
