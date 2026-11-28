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
            with (
                patch("apps.orcUi.map_theme_runtime.Path.write_text", side_effect=PermissionError),
                self.assertLogs("apps.orcUi.map_theme_runtime", level="WARNING") as logs,
            ):
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
            self.assertIn('"background-color":"#103f56"', style)
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
            (root / "maps" / "vector").mkdir(parents=True)
            (root / "maps" / "vector" / "us-freeways.mbtiles").touch()
            destination = install_map_style(ThemeMode.DARK, root)
            document = json.loads(destination.read_text(encoding="utf-8"))
            layers = {layer["id"]: layer for layer in document["layers"]}
            self.assertEqual(layers["state-boundaries"]["paint"]["line-color"], "#9cd6ac")
            self.assertEqual(
                layers["canadian-boundaries"]["paint"], layers["state-boundaries"]["paint"]
            )
            self.assertEqual(layers["reference-land"]["paint"]["fill-color"], "#18372b")
            self.assertEqual(layers["reference-lakes"]["paint"]["fill-color"], "#103f56")
            self.assertEqual(layers["national-motorways"]["source"], "national-freeways")
            self.assertEqual(layers["motorways"]["source"], "openroad")
            self.assertEqual(layers["state-boundaries"]["minzoom"], 0)
            self.assertIn(
                "us_state_internal_boundaries.geojson",
                document["sources"]["state-boundaries"]["data"],
            )
            self.assertEqual(layers["state-boundaries"]["paint"]["line-dasharray"], [3, 1.5])
            canada_asset = root / "maps" / "boundaries" / "ca_province_territory_boundaries.geojson"
            self.assertIn(canada_asset.name, document["sources"]["canadian-boundaries"]["data"])
            self.assertTrue(canada_asset.is_file())
            self.assertEqual(layers["country-boundaries"]["paint"]["line-color"], "#dce8ef")
            self.assertEqual(layers["michigan-boundary"]["paint"]["line-color"], "#59d8ff")
            self.assertEqual(layers["buildings"]["type"], "fill-extrusion")
            self.assertIn("fill-extrusion-color", layers["buildings"]["paint"])
            self.assertIn("poi-results", document["sources"])
            self.assertIn("poi-results-icon", layers)

    def test_missing_national_freeways_preserves_regional_motorways(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "maps" / "styles").mkdir(parents=True)
            document = json.loads(install_map_style(ThemeMode.DARK, root).read_text())
            layers = {layer["id"]: layer for layer in document["layers"]}
            self.assertNotIn("national-freeways", document["sources"])
            self.assertNotIn("freeway-labels-national", layers)
            self.assertNotIn("national-motorways", layers)
            self.assertEqual(layers["motorways"]["source"], "openroad")
            self.assertEqual(layers["road-refs-major"]["source"], "openroad")
            self.assertEqual(layers["road-refs-major"]["filter"], ["has", "ref"])
            self.assertNotIn("filter", layers["road-labels"])

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
            self.assertIn('"background-color":"#75bee3"', style)


if __name__ == "__main__":
    unittest.main()


def test_theme_upgrade_installs_missing_global_reference_sources(tmp_path):
    (tmp_path / "maps/styles").mkdir(parents=True)
    document = json.loads(install_map_style(ThemeMode.DARK, tmp_path).read_text())
    for name in ("reference-land", "reference-lakes", "country-boundaries", "state-boundaries"):
        filename = Path(document["sources"][name]["data"]).name
        data = json.loads((tmp_path / "maps/boundaries" / filename).read_text())
        assert data["type"] == "FeatureCollection"
        assert data["features"]
