# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for atomic filesystem cache storage."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from controllers.cache import PersistentCache


class PersistentCacheTest(unittest.TestCase):
    def test_bytes_survive_across_instances(self) -> None:
        with TemporaryDirectory() as directory:
            first = PersistentCache(directory)
            first.put("weather:current", b'{"temperature": 20}')

            second = PersistentCache(directory)

            self.assertEqual(
                b'{"temperature": 20}',
                second.get("weather:current"),
            )
            self.assertEqual(
                1,
                len(tuple(Path(directory).glob("*.cache"))),
            )

    def test_remove_reports_presence(self) -> None:
        with TemporaryDirectory() as directory:
            cache = PersistentCache(directory)
            cache.put("entry", b"value")

            self.assertTrue(cache.remove("entry"))
            self.assertFalse(cache.remove("entry"))
            self.assertIsNone(cache.get("entry"))

    def test_empty_key_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            cache = PersistentCache(directory)

            with self.assertRaises(ValueError):
                cache.get("  ")


if __name__ == "__main__":
    unittest.main()
