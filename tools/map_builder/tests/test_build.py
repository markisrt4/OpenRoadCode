# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tools.map_builder.builder.build import REFERENCE_MAP_FILES, BuildError, _build_maplibre_data, _build_national_freeways, _download, _download_and_verify, _merge_for_build, _parse_bbox, _prepare_output_dirs


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

    def test_maplibre_build_packages_reference_map_assets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "reference-source"
            source.mkdir()
            for name in REFERENCE_MAP_FILES:
                (source / name).write_text('{"type":"FeatureCollection","features":[{}]}')
            with (
                patch("tools.map_builder.builder.build.OUTPUT_ROOT", root / "output"),
                patch("tools.map_builder.builder.build.REFERENCE_MAP_SOURCE", source),
                patch("tools.map_builder.builder.build._build_vector_tiles"),
                patch("tools.map_builder.builder.build.install_style"),
                patch("tools.map_builder.builder.build.shutil.copytree"),
            ):
                _build_maplibre_data(Path("regional.osm.pbf"))
            for name in REFERENCE_MAP_FILES:
                self.assertEqual(
                    (root / "output/maps/boundaries" / name).read_bytes(),
                    (source / name).read_bytes(),
                )


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
                "osmium",
                "merge",
                "--with-history",
                "--overwrite",
                "-f",
                "pbf,history=true",
                "-o",
                str(history),
                str(pbfs[0]),
                str(pbfs[1]),
            ],
        )
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["osmium", "time-filter", "--overwrite", "-o", str(expected_merged), str(history)],
        )
        self.assertEqual(
            run.call_args_list[2].args[0], ["osmium", "fileinfo", "-e", str(expected_merged)]
        )


class GeofabrikCacheTests(unittest.TestCase):
    def test_large_download_resumes_partial_file_with_bounded_retries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "us.osm.pbf"
            partial = destination.with_suffix(".pbf.part")
            partial.write_bytes(b"partial")

            def finish(_command):
                partial.write_bytes(partial.read_bytes() + b"-complete")

            with patch("tools.map_builder.builder.build.run", side_effect=finish) as run:
                _download("https://example.invalid/us.osm.pbf", destination)

            command = run.call_args.args[0]
            self.assertIn("--retry-all-errors", command)
            self.assertIn("--continue-at", command)
            self.assertEqual(command[command.index("--continue-at") + 1], "-")
            self.assertEqual(destination.read_bytes(), b"partial-complete")
            self.assertFalse(partial.exists())

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
                patch(
                    "tools.map_builder.builder.build._download", side_effect=fake_download
                ) as download,
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


class NationalFreewayBuildTests(unittest.TestCase):
    def test_reprojects_census_primary_roads_and_builds_compatible_layers(self):
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("tools.map_builder.builder.build.SCRATCH_ROOT", Path(tmpdir)),
            patch("tools.map_builder.builder.build.OUTPUT_ROOT", Path(tmpdir) / "output"),
            patch("tools.map_builder.builder.build.run") as run,
            patch("tools.map_builder.builder.build._sha256_file", return_value="abc123"),
        ):
            source = Path(tmpdir) / "tl_2026_us_primaryroads.zip"
            source.write_bytes(b"census archive fixture")
            result = _build_national_freeways(source)
            shapefile = Path(tmpdir) / "us-primary-roads/tl_2026_us_primaryroads.shp"
            self.assertEqual(run.call_args_list[0].args[0], [
                "ogr2ogr", "-f", "ESRI Shapefile", "-t_srs", "EPSG:4326",
                str(shapefile), f"/vsizip/{source}/tl_2026_us_primaryroads.shp",
            ])
            tilemaker = run.call_args_list[1].args[0]
            self.assertEqual(tilemaker[0], "tilemaker")
            self.assertIn("us-freeways.mbtiles", " ".join(tilemaker))
            config = json.loads((Path(tmpdir) / "census-primary-roads.json").read_text())
            self.assertEqual(set(config["layers"]), {"transportation", "transportation_name"})
            self.assertEqual(result["archive_sha256"], "abc123")

    def test_build_downloads_national_source_before_output_cleanup(self):
        from tools.map_builder.builder.build import build_regions

        regional = SimpleNamespace(id="us/michigan")
        source = Path("/cache/census/tl_2026_us_primaryroads.zip")
        events = []
        with (
            patch("tools.map_builder.builder.build._national_freeway_archive",
                  side_effect=lambda: events.append(("download", "census")) or source),
            patch("tools.map_builder.builder.build._download_and_verify", return_value=source),
            patch("tools.map_builder.builder.build._prepare_output_dirs",
                  side_effect=lambda **_kwargs: events.append(("prepare", None))),
            patch("tools.map_builder.builder.build._install_sources", return_value=[source]),
            patch("tools.map_builder.builder.build._merge_for_build", return_value=(source, None)),
            patch("tools.map_builder.builder.build.build_search_index", return_value={}),
            patch("tools.map_builder.builder.build._build_maplibre_data"),
            patch("tools.map_builder.builder.build._build_national_freeways"),
            patch("tools.map_builder.builder.build._build_valhalla"),
            patch("tools.map_builder.builder.build.validate_output", return_value={"map_3d": {}}),
            patch("tools.map_builder.builder.build._write_manifest"),
        ):
            build_regions([regional])

        self.assertEqual(events[0], ("download", "census"))
        self.assertEqual(events[1], ("prepare", None))


if __name__ == "__main__":
    unittest.main()
