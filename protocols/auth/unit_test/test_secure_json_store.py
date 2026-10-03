# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import os
from pathlib import Path
import stat
import tempfile
import unittest

from protocols.auth.secure_json_store import SecureJsonStore


class SecureJsonStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "auth" / "credentials.json"
        self.store = SecureJsonStore(self.path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_missing_record_loads_none(self) -> None:
        self.assertIsNone(self.store.load())

    def test_save_and_load_record(self) -> None:
        record = {"access_token": "secret", "nested": {"enabled": True}}
        self.store.save(record)
        self.assertEqual(self.store.load(), record)

    def test_save_restricts_directory_and_file_permissions(self) -> None:
        previous_umask = os.umask(0)
        try:
            self.store.save({"secret": "value"})
        finally:
            os.umask(previous_umask)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_save_repairs_existing_permissions(self) -> None:
        self.path.parent.mkdir(mode=0o755)
        self.path.write_text("{}", encoding="utf-8")
        self.path.chmod(0o644)
        self.store.save({"secret": "value"})
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_clear_removes_record(self) -> None:
        self.store.save({"secret": "value"})
        self.store.clear()
        self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
