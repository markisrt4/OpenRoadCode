# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.map_builder.builder.cli import (
    directory_size,
    format_duration,
    format_size,
    reusable_build_for_regions,
)


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


class ReusableBuildTests(unittest.TestCase):
    def test_reuses_matching_validated_regions_regardless_of_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build-manifest.json").write_text(
                json.dumps(
                    {
                        "schema": 2,
                        "regions": [
                            {"id": "north-america/us/ohio"},
                            {"id": "north-america/us/michigan"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            selected = [
                SimpleNamespace(id="north-america/us/michigan"),
                SimpleNamespace(id="north-america/us/ohio"),
            ]
            validation = {"mbtiles": {"tiles": 1}}
            with patch(
                "tools.map_builder.builder.cli.validate_output",
                return_value=validation,
            ) as validate:
                result = reusable_build_for_regions(
                    selected,
                    root=root,
                    service_smoke=False,
                )

            self.assertIs(result, validation)
            validate.assert_called_once_with(root, service_smoke=False)

    def test_rejects_manifest_for_different_regions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build-manifest.json").write_text(
                json.dumps(
                    {
                        "schema": 2,
                        "regions": [{"id": "north-america/us/michigan"}],
                    }
                ),
                encoding="utf-8",
            )
            selected = [SimpleNamespace(id="north-america/us/ohio")]
            with patch("tools.map_builder.builder.cli.validate_output") as validate:
                result = reusable_build_for_regions(
                    selected,
                    root=root,
                    service_smoke=False,
                )

            self.assertIsNone(result)
            validate.assert_not_called()

    def test_rejects_matching_manifest_when_validation_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build-manifest.json").write_text(
                json.dumps(
                    {
                        "schema": 2,
                        "regions": [{"id": "north-america/us/michigan"}],
                    }
                ),
                encoding="utf-8",
            )
            selected = [SimpleNamespace(id="north-america/us/michigan")]
            with patch(
                "tools.map_builder.builder.cli.validate_output",
                side_effect=RuntimeError("bad output"),
            ):
                result = reusable_build_for_regions(
                    selected,
                    root=root,
                    service_smoke=False,
                )

            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()


class Optional3DRecoveryTests(unittest.TestCase):
    def test_failed_extraction_restores_unchanged_base_certificate(self):
        from tools.map_builder.builder import cli
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=b'{"schema":2,"regions":[],"validation":{}}\n'
            (root/'build-manifest.json').write_bytes(original)
            args=SimpleNamespace(command='3d',coverage='detroit-midtown',yes=True)
            with (patch.object(cli,'parse_args',return_value=args),
                  patch.object(cli,'OUTPUT_ROOT',root),
                  patch.object(cli,'validate_output',return_value={'map_3d':{}}),
                  patch('tools.map_builder.builder.map_3d.build_pack',side_effect=ValueError('empty export'))):
                self.assertEqual(cli.main(),2)
            self.assertEqual((root/'build-manifest.json').read_bytes(),original)

    def test_recovery_infers_all_installed_source_region_ids(self):
        from tools.map_builder.builder import cli
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sources=root/'maps/source'
            sources.mkdir(parents=True)
            for state in ('michigan','ohio'):
                (sources/f'north-america__us__{state}.osm.pbf').write_bytes(b'fixture')
            args=SimpleNamespace(command='validate',installed_regions=True,regions=None,
                                 write_manifest=True,service_smoke=False,refresh_index=False,json=False)
            with (patch.object(cli,'parse_args',return_value=args),
                  patch.object(cli,'OUTPUT_ROOT',root),
                  patch.object(cli,'validate_output',return_value={'source_pbfs':2}),
                  patch.object(cli,'fetch_index',return_value=[]),
                  patch.object(cli,'resolve_region_ids',return_value=[Mock(),Mock()]) as resolve,
                  patch.object(cli,'_write_manifest') as write,
                  patch.object(cli,'print_validation_summary')):
                self.assertEqual(cli.main(),0)
                self.assertEqual(resolve.call_args.args[1],['north-america/us/michigan','north-america/us/ohio'])
                write.assert_called_once()
