# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for ORC MapLibre theme generation."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.orcUi.map_theme_runtime import _default_data_root, install_map_style
from ui.theme import ThemeMode


class MapThemeRuntimeTest(unittest.TestCase):
    def test_read_only_deployed_style_survives_a_theme_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            style = root / "maps/styles/openroadcode.json"
            style.parent.mkdir(parents=True)
            style.write_text('{"version":8}')
            with (patch("apps.orcUi.map_theme_runtime.Path.write_text", side_effect=PermissionError),
                  self.assertLogs("apps.orcUi.map_theme_runtime", level="WARNING") as logs):
                self.assertEqual(install_map_style(ThemeMode.DARK, root), style)
            self.assertEqual(style.read_text(), '{"version":8}')
            self.assertIn("install_navigation_style.sh", logs.output[0])

    @patch.dict(os.environ, {"OPENROADCODE_DATA_ROOT": "/tmp/orc-map-data"}, clear=False)
    def test_explicit_data_root_environment_wins(self) -> None:
        self.assertEqual(_default_data_root(), Path("/tmp/orc-map-data"))

    @patch.dict(os.environ, {}, clear=True)
    @patch("apps.orcUi.map_theme_runtime.Path.is_dir", return_value=True)
    def test_deployed_linux_data_root_is_preferred(self, _is_dir) -> None:
        self.assertEqual(_default_data_root(), Path("/srv/openroadcode"))

    def test_dark_style_uses_known_good_semantic_palette(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            (data_root / "maps" / "styles").mkdir(parents=True)

            destination = install_map_style(ThemeMode.DARK, data_root)

            self.assertEqual(destination, data_root / "maps" / "styles" / "openroadcode.json")
            style = destination.read_text(encoding="utf-8")
            self.assertIn('"background-color":"#0b151b"', style)
            self.assertIn('"farmland","#2d3f35"', style)
            self.assertIn('"fill-color":"#103f56"', style)
            self.assertIn('"line-color":"#4c8297"', style)
            self.assertIn('"commercial","#493044"', style)
            self.assertIn('"hospital","#542f42"', style)
            self.assertIn('"school","#24525a"', style)
            self.assertIn('"poi-results":{"type":"geojson"', style)
            self.assertIn('"id":"poi-results-glow"', style)
            self.assertIn('"id":"poi-results-icon"', style)
            self.assertIn('"id":"poi-results-label"', style)

    def test_state_boundaries_coexist_with_3d_buildings_and_poi_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "maps" / "styles").mkdir(parents=True)
            destination = install_map_style(ThemeMode.DARK, root)
            document = json.loads(destination.read_text(encoding="utf-8"))
            layers = {layer["id"]: layer for layer in document["layers"]}
            self.assertEqual(layers["state-boundaries"]["paint"]["line-color"], "#54c96b")
            self.assertEqual(layers["buildings"]["type"], "fill-extrusion")
            self.assertIn("fill-extrusion-color", layers["buildings"]["paint"])
            self.assertIn("poi-results", document["sources"])
            self.assertIn("poi-results-icon", layers)

    def test_radar_locator_rings_follow_vehicle_above_radar_and_below_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "maps" / "styles").mkdir(parents=True)
            document = json.loads(install_map_style(ThemeMode.DARK, root).read_text())
            layers = document["layers"]
            by_id = {layer["id"]: layer for layer in layers}
            ids = [layer["id"] for layer in layers]
            for name, radius in (("inner", 36), ("middle", 72), ("outer", 108)):
                layer_id = f"radar-position-ring-{name}"
                layer = by_id[layer_id]
                self.assertEqual(layer["source"], "vehicle")
                self.assertEqual(layer["paint"]["circle-radius"], radius)
                self.assertEqual(layer["paint"]["circle-opacity"], 0)
                self.assertEqual(layer["layout"]["visibility"], "none")
                self.assertGreater(ids.index(layer_id), ids.index("route-line-casing"))
                self.assertLess(ids.index(layer_id), ids.index("vehicle-blue-dot"))

    def test_light_style_uses_distinct_school_teal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            (data_root / "maps" / "styles").mkdir(parents=True)

            destination = install_map_style(ThemeMode.LIGHT, data_root)

            style = destination.read_text(encoding="utf-8")
            self.assertIn('"school","#c9e4e2"', style)
            self.assertIn('"fill-color":"#a9dcb7"', style)


if __name__ == "__main__":
    unittest.main()
