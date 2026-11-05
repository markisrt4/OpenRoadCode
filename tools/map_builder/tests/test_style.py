# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from pathlib import Path
import json
import tempfile
import unittest

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
        self.assertIn("us_state_internal_boundaries.geojson",
                      document["sources"]["state-boundaries"]["data"])
        self.assertEqual(document["sources"]["country-boundaries"]["type"], "geojson")
        self.assertEqual(layers["state-boundaries"]["paint"]["line-dasharray"], [1, 2])
        self.assertEqual(layers["michigan-boundary"]["filter"][-1], "26")

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

if __name__ == "__main__": unittest.main()
