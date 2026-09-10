# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tools.map_builder.builder.build import BuildError, _download_and_verify, _parse_bbox


class BoundingBoxTests(unittest.TestCase):
    def test_parse_plain_bbox(self):
        self.assertEqual(
            _parse_bbox("-90.5,41.2,-80.1,48.3"),
            "-90.5,41.2,-80.1,48.3",
        )

    def test_parse_osmium_box_format(self):
        self.assertEqual(
            _parse_bbox("BOX(-90.5 41.2,-80.1 48.3)"),
            "-90.5,41.2,-80.1,48.3",
        )

    def test_reject_invalid_bbox(self):
        with self.assertRaises(BuildError):
            _parse_bbox("not a bounding box")

        with self.assertRaises(BuildError):
            _parse_bbox("10,20,-10,30")


class GeofabrikCacheTests(unittest.TestCase):
    def test_stale_cached_pbf_is_refreshed(self):
        fresh = b"fresh geofabrik data"
        expected = hashlib.md5(fresh).hexdigest()
        region = SimpleNamespace(
            id="us/michigan",
            safe_id="us__michigan",
            pbf_url="https://example.invalid/michigan-latest.osm.pbf",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            cached = cache_root / "pbf" / "us__michigan.osm.pbf"
            cached.parent.mkdir(parents=True)
            cached.write_bytes(b"stale data")

            checksum_response = Mock()
            checksum_response.__enter__ = Mock(return_value=checksum_response)
            checksum_response.__exit__ = Mock(return_value=False)
            checksum_response.read.return_value = f"{expected}  michigan-latest.osm.pbf\n".encode()

            def fake_download(_url, destination):
                destination.write_bytes(fresh)

            with (
                patch("tools.map_builder.builder.build.CACHE_ROOT", cache_root),
                patch("tools.map_builder.builder.build.urlopen", return_value=checksum_response),
                patch("tools.map_builder.builder.build._download", side_effect=fake_download) as download,
                patch("tools.map_builder.builder.build.run"),
            ):
                result = _download_and_verify(region)

            self.assertEqual(result, cached)
            self.assertEqual(cached.read_bytes(), fresh)
            download.assert_called_once_with(region.pbf_url, cached)

    def test_bad_fresh_download_still_fails(self):
        expected = hashlib.md5(b"expected data").hexdigest()
        region = SimpleNamespace(
            id="us/michigan",
            safe_id="us__michigan",
            pbf_url="https://example.invalid/michigan-latest.osm.pbf",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            checksum_response = Mock()
            checksum_response.__enter__ = Mock(return_value=checksum_response)
            checksum_response.__exit__ = Mock(return_value=False)
            checksum_response.read.return_value = f"{expected}  michigan-latest.osm.pbf\n".encode()

            def fake_download(_url, destination):
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b"wrong data")

            with (
                patch("tools.map_builder.builder.build.CACHE_ROOT", cache_root),
                patch("tools.map_builder.builder.build.urlopen", return_value=checksum_response),
                patch("tools.map_builder.builder.build._download", side_effect=fake_download),
                patch("tools.map_builder.builder.build.run"),
            ):
                with self.assertRaisesRegex(
                    BuildError,
                    "MD5 mismatch for freshly downloaded us/michigan",
                ):
                    _download_and_verify(region)


if __name__ == "__main__":
    unittest.main()
