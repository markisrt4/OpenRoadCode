# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import json
from pathlib import Path
import tempfile
import unittest

from tools.map_builder.builder.selection import load_region_ids, save_region_ids


class SelectionPersistenceTests(unittest.TestCase):
    def test_missing_file_has_no_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_region_ids(Path(directory) / "missing.json"), set())

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "selected-regions.json"
            save_region_ids(path, ["north-america/us/ohio", "north-america/us/michigan"])

            self.assertEqual(
                load_region_ids(path),
                {"north-america/us/michigan", "north-america/us/ohio"},
            )
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["regions"],
                ["north-america/us/michigan", "north-america/us/ohio"],
            )

    def test_reject_invalid_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "selected-regions.json"
            path.write_text('{"schema": 1, "regions": "ohio"}', encoding="utf-8")

            with self.assertRaises(ValueError):
                load_region_ids(path)


if __name__ == "__main__":
    unittest.main()
