# SPDX-License-Identifier: MIT
"""Fail-closed credential provisioning tests."""

from io import BytesIO
import json
import os
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest.mock import patch

from services.common.service_manager_sms_provision import serve_sms_provision


class Handler:
    path = "/sms/provision"
    client_address = ("127.0.0.1", 12345)

    def __init__(self, auth=None, body=b""):
        self.headers = {"Content-Length": str(len(body))}
        if auth is not None:
            self.headers["Authorization"] = auth
        self.rfile = BytesIO(body)
        self.result = None

    def _json(self, status, payload):
        self.result = (status.value, payload)


class SmsProvisionTest(unittest.TestCase):
    def test_missing_config_or_wrong_token_fails_closed(self):
        for env, auth in (({}, None), ({"OPENROADCODE_SMS_PROVISION_TOKEN": "a" * 43}, "Bearer wrong")):
            with patch.dict(os.environ, env, clear=True):
                handler = Handler(auth)
                self.assertTrue(serve_sms_provision(handler, "GET"))
                self.assertEqual(handler.result[0], 401)

    def test_provision_and_revoke_never_return_secret(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "sms-token"
            secret = "s" * 43
            env = {"OPENROADCODE_SMS_PROVISION_TOKEN": "p" * 43}
            with patch.dict(os.environ, env, clear=True), patch(
                "services.common.service_manager_sms_provision.save_token"
            ) as save, patch(
                "services.common.service_manager_sms_provision.load_token", return_value=secret
            ), patch(
                "services.common.service_manager_sms_provision.delete_token"
            ) as delete:
                handler = Handler("Bearer " + "p" * 43, json.dumps({"token": secret}).encode())
                self.assertTrue(serve_sms_provision(handler, "POST"))
                self.assertEqual(handler.result, (200, {"provisioned": True}))
                save.assert_called_once_with(secret)
                status = Handler("Bearer " + "p" * 43)
                serve_sms_provision(status, "GET")
                self.assertEqual(status.result, (200, {"provisioned": True}))
                self.assertNotIn(secret, str(status.result))
                revoke = Handler("Bearer " + "p" * 43)
                serve_sms_provision(revoke, "DELETE")
                self.assertEqual(revoke.result, (200, {"provisioned": False}))
                delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
