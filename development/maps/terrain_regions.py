"""Versioned rectangular terrain build plans; envelopes are not political boundaries."""

import argparse
import json
from pathlib import Path

MICHIGAN_BOUNDS = (-90.5, 41.7, -82.1, 48.3)

MICHIGAN_SHARDS = {
    "mi-lower-southwest": ("Michigan Lower Peninsula southwest", (-86.5, 41.7, -84.3, 43.5)),
    "mi-lower-southeast": ("Michigan Lower Peninsula southeast", (-84.3, 41.7, -82.1, 43.5)),
    "mi-lower-central-west": ("Michigan Lower Peninsula central west", (-86.5, 43.5, -84.3, 45.3)),
    "mi-lower-central-east": ("Michigan Lower Peninsula central east", (-84.3, 43.5, -82.1, 45.3)),
    "mi-lower-northwest": ("Michigan Lower Peninsula northwest", (-86.5, 45.3, -84.3, 46.5)),
    "mi-lower-northeast": ("Michigan Lower Peninsula northeast", (-84.3, 45.3, -82.1, 46.5)),
    "mi-upper-west": ("Michigan Upper Peninsula west", (-90.5, 45.5, -87.0, 48.3)),
    "mi-upper-east": ("Michigan Upper Peninsula east", (-87.0, 45.5, -83.5, 48.3)),
}

MICHIGAN_COVERAGES = {
    "michigan-overview": ("Michigan statewide terrain overview", MICHIGAN_BOUNDS),
    **MICHIGAN_SHARDS,
}


def catalog_document():
    return {
        "schema": 1,
        "kind": "terrain-catalog",
        "coverage": "michigan",
        "bounds_deg": MICHIGAN_BOUNDS,
        "overview": "michigan-overview",
        "detail_shards": [
            {"coverage": coverage, "title": title, "bounds_deg": bounds}
            for coverage, (title, bounds) in MICHIGAN_SHARDS.items()
        ],
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
