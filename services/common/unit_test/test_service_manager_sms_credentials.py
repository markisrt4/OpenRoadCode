# SPDX-License-Identifier: MIT
"""Credential file must remain private and reject unsafe inputs."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.common.service_manager_sms_credentials import (
    delete_token,
    load_token,
    save_token,
)


class SmsCredentialsTest(unittest.TestCase):
    def test_round_trip_private_permissions_and_delete(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "sms"
            self.assertIsNone(load_token(path))
            save_token("a" * 43, path)
            self.assertEqual(load_token(path), "a" * 43)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            delete_token(path)
            self.assertIsNone(load_token(path))

    def test_short_or_multiline_credentials_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sms"
            for token in ("short", "a" * 40 + "\n" + "b" * 40):
                with self.assertRaises(ValueError):
                    save_token(token, path)
            self.assertFalse(path.exists())

    def test_insecure_file_not_loaded(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "sms"
            path.write_text("a" * 43)
            os.chmod(path, 0o644)
            self.assertIsNone(load_token(path))


if __name__ == "__main__":
    unittest.main()
