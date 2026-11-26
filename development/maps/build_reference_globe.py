"""Rasterize the bundled world reference once, outside the device GPU path."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
LAND = "#456f4e"
WATER = "#174963"


def paint(image, collection, color):
    width, height = image.size

    def project(point):
        return ((point[0] + 180) * width / 360, (90 - point[1]) * height / 180)

    for feature in collection["features"]:
        geometry = feature["geometry"]
        polygons = (
            [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        )
        for polygon in polygons:
            # Holes are local to their polygon; disjoint/overlapping members do
            # not cancel one another through a feature-wide even/odd fill.
            mask = Image.new("L", image.size)
            draw = ImageDraw.Draw(mask)
            for index, ring in enumerate(polygon):
                draw.polygon([project(point) for point in ring], fill=255 if index == 0 else 0)
            image.paste(color, mask=mask)


def build(output):
    image = Image.new("RGB", (2048, 1024), WATER)
    for filename, color in (("world_land.geojson", LAND), ("world_lakes.geojson", WATER)):
        paint(image, json.loads((ROOT / "resources/maps" / filename).read_text()), color)
    image.save(output, optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
