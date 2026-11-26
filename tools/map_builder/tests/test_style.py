# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import json
import tempfile
import unittest
from pathlib import Path

from tools.map_builder.builder.style import install_style
from tools.map_builder.builder.validate import validate_style

TEMPLATE = Path(__file__).parents[1] / "templates/openroadcode-style.json"


class StyleTests(unittest.TestCase):
    def test_style_round_trip_and_required_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "style.json"
            install_style(TEMPLATE, destination)
            validate_style(destination)

    def test_shared_political_boundary_sources_and_styles(self):
        document = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        layers = {layer["id"]: layer for layer in document["layers"]}
        self.assertEqual(document["sources"]["state-boundaries"]["type"], "geojson")
        self.assertIn("us_state_boundaries.geojson",
                      document["sources"]["state-boundaries"]["data"])
        self.assertEqual(document["sources"]["country-boundaries"]["type"], "geojson")
        self.assertEqual(layers["state-boundaries"]["paint"]["line-dasharray"], [1, 2])
        self.assertEqual(layers["michigan-boundary"]["filter"][-1], "26")
        self.assertEqual(layers["state-boundaries"]["minzoom"], 0)
        self.assertEqual(layers["michigan-boundary"]["minzoom"], 0)
        asset = TEMPLATE.parents[3]/'resources/maps/us_state_boundaries.geojson'
        self.assertEqual(len(json.loads(asset.read_text())['features']), 50)

    def test_national_reference_land_and_freeways_are_layered_below_boundaries(self):
        document = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        sources = document["sources"]
        layers = {layer["id"]: layer for layer in document["layers"]}
        order = [layer["id"] for layer in document["layers"]]
        self.assertIn("world_land.geojson", sources["reference-land"]["data"])
        self.assertIn("world_lakes.geojson", sources["reference-lakes"]["data"])
        self.assertIn("us-freeways.mbtiles", sources["national-freeways"]["url"])
        self.assertEqual(layers["reference-coastlines"]["source"], "reference-land")
        self.assertNotIn("line-dasharray", layers["reference-coastlines"]["paint"])
        self.assertLess(order.index("reference-coastlines"), order.index("country-boundaries"))
        self.assertEqual(layers["national-motorways"]["source"], "national-freeways")
        self.assertEqual(layers["national-motorways-casing"]["source"], "national-freeways")
        self.assertEqual(layers["motorways"]["source"], "openroad")
        self.assertEqual(layers["motorways-casing"]["source"], "openroad")
        self.assertEqual(layers["national-motorways"]["paint"]["line-width"][0], "interpolate")
        self.assertEqual(layers["motorways"]["paint"]["line-width"][0], "interpolate")
        self.assertLess(order.index("reference-land"), order.index("state-boundaries"))
        self.assertLess(order.index("reference-lakes"), order.index("state-boundaries"))
        self.assertTrue((TEMPLATE.parents[3] / "resources/maps/world_land.geojson").is_file())
        self.assertTrue((TEMPLATE.parents[3] / "resources/maps/world_lakes.geojson").is_file())

    def test_buildings_use_height_aware_3d_extrusions(self):
        document = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        buildings = next(layer for layer in document["layers"] if layer["id"] == "buildings")
        self.assertEqual(buildings["type"], "fill-extrusion")
        self.assertEqual(
            buildings["paint"]["fill-extrusion-height"],
            ["coalesce", ["get", "render_height"], 3.66],
        )
        self.assertEqual(
            buildings["paint"]["fill-extrusion-base"],
            ["coalesce", ["get", "render_min_height"], 0],
        )


if __name__ == "__main__":
    unittest.main()
