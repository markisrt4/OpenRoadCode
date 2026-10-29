"""Write the installable Michigan imagery coverage catalog."""

import argparse
import json
from pathlib import Path

from development.maps.terrain_regions import MICHIGAN_BOUNDS, MICHIGAN_SHARDS


def catalog_document():
    return {
        "schema": 1,
        "kind": "imagery-catalog",
        "coverage": "michigan",
        "bounds_deg": MICHIGAN_BOUNDS,
        "overview": "michigan-overview",
        "detail_shards": [
            {"coverage": coverage, "title": title.replace("terrain", "imagery"),
             "bounds_deg": bounds}
            for coverage, (title, bounds) in MICHIGAN_SHARDS.items()
        ],
        "image_pixels": [8192, 8192],
        "notes": "Rectangular planning envelopes include water and neighboring areas.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog_document(), indent=2))


if __name__ == "__main__":
    main()
