# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

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
