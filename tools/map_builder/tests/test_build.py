# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tools.map_builder.builder.build import BuildError, _download_and_verify, _merge_for_build, _parse_bbox, _prepare_output_dirs


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


class OutputPreparationTests(unittest.TestCase):
    def test_clean_build_invalidates_existing_manifest_before_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "build-manifest.json"
            manifest.write_text('{"schema": 1}\n', encoding="utf-8")
            (root / "maps/vector").mkdir(parents=True)
            (root / "maps/vector/stale.mbtiles").write_bytes(b"stale")

            with (
                patch("tools.map_builder.builder.build.OUTPUT_ROOT", root),
                patch("tools.map_builder.builder.build.SCRATCH_ROOT", root / "scratch"),
            ):
                _prepare_output_dirs(clean=True)

            self.assertFalse(manifest.exists())
            self.assertFalse((root / "maps/vector/stale.mbtiles").exists())
            self.assertTrue((root / "maps/vector").is_dir())


class MultiRegionMergeTests(unittest.TestCase):
    def test_multi_region_merge_collapses_overlapping_object_versions(self):
        pbfs = [Path("/tmp/michigan.osm.pbf"), Path("/tmp/ohio.osm.pbf")]
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("tools.map_builder.builder.build.SCRATCH_ROOT", Path(tmpdir)),
            patch("tools.map_builder.builder.build.run") as run,
            patch("tools.map_builder.builder.build._pbf_bbox", return_value="-90,40,-80,49"),
        ):
            merged, bbox = _merge_for_build(pbfs)

        history = Path(tmpdir) / "selected-regions-history.osh.pbf"
        expected_merged = Path(tmpdir) / "selected-regions.osm.pbf"
        self.assertEqual(merged, expected_merged)
        self.assertEqual(bbox, "-90,40,-80,49")
        self.assertEqual(run.call_count, 3)
        self.assertEqual(
            run.call_args_list[0].args[0],
            [
                "osmium", "merge", "--with-history", "--overwrite",
                "-f", "pbf,history=true", "-o", str(history),
                str(pbfs[0]), str(pbfs[1]),
            ],
        )
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["osmium", "time-filter", "--overwrite", "-o", str(expected_merged), str(history)],
        )
        self.assertEqual(run.call_args_list[2].args[0], ["osmium", "fileinfo", "-e", str(expected_merged)])


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
