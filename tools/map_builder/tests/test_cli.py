# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest
from pathlib import Path
import tempfile

from builder.cli import directory_size, format_duration, format_size


class BuildSummaryFormattingTests(unittest.TestCase):
    def test_format_duration(self):
        self.assertEqual(format_duration(42.4), "42s")
        self.assertEqual(format_duration(125), "2m 5s")
        self.assertEqual(format_duration(7384), "2h 3m 4s")

    def test_format_size(self):
        self.assertEqual(format_size(512), "512 B")
        self.assertEqual(format_size(5 * 1024 * 1024), "5.00 MiB")
        self.assertEqual(format_size(3 * 1024**3), "3.00 GiB")

    def test_directory_size(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "maps").mkdir()
            (root / "maps/vector.mbtiles").write_bytes(b"map-data")
            (root / "manifest.json").write_bytes(b"manifest")

            self.assertEqual(directory_size(root), 16)


if __name__ == "__main__":
    unittest.main()
