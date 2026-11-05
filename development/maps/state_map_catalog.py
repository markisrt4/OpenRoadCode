"""Generate repeatable overview and detail build regions for all 50 states."""

import argparse
import json
import math
from pathlib import Path

from development.maps.terrain_regions import (MICHIGAN_BOUNDS, MICHIGAN_SHARDS)

_BOUNDARIES = Path(__file__).resolve().parents[2] / "resources/maps/us_state_boundaries.geojson"
_TARGET_SHARD_SPAN_M = 260_000


def _coordinates(value):
    if (isinstance(value, list) and len(value) >= 2
            and all(isinstance(item, (int, float)) for item in value[:2])):
        yield float(value[0]), float(value[1])
    elif isinstance(value, list):
        for item in value:
            yield from _coordinates(item)


def _feature_bounds(feature):
    points = tuple(_coordinates(feature["geometry"]["coordinates"]))
    latitudes = [point[1] for point in points]
    longitudes = sorted((point[0] + 360) % 360 for point in points)
    gaps = [(longitudes[(index + 1) % len(longitudes)] - longitude) % 360
            for index, longitude in enumerate(longitudes)]
    split = max(range(len(gaps)), key=gaps.__getitem__)
    west = longitudes[(split + 1) % len(longitudes)]
    east = longitudes[split]
    if east < west:
        east += 360
    while west > 180:
        west -= 360
        east -= 360
    return west, min(latitudes), east, max(latitudes)


def _regions(bounds, abbreviation, group=""):
    west, south, east, north = bounds
    latitude = (south + north) / 2
    width_m = (east - west) * 111_320 * max(.2, math.cos(math.radians(latitude)))
    height_m = (north - south) * 111_320
    columns = max(1, math.ceil(width_m / _TARGET_SHARD_SPAN_M))
    rows = max(1, math.ceil(height_m / _TARGET_SHARD_SPAN_M))
    result = []
    for row in range(rows):
        for column in range(columns):
            region = (west + (east-west)*column/columns,
                      south + (north-south)*row/rows,
                      west + (east-west)*(column+1)/columns,
                      south + (north-south)*(row+1)/rows)
            result.append({"coverage": f"us-{abbreviation.lower()}-detail-{group}r{row}-c{column}",
                           "title": f"{abbreviation} detail {row + 1}-{column + 1}",
                           "bounds_deg": region})
    return result


def catalog_document():
    source = json.loads(_BOUNDARIES.read_text())
    states = []
    for feature in sorted(source["features"], key=lambda item: item["properties"]["STUSAB"]):
        properties = feature["properties"]
        abbreviation = properties["STUSAB"]
        bounds = _feature_bounds(feature)
        if abbreviation == "MI":
            overview = {"coverage": "michigan-overview", "bounds_deg": MICHIGAN_BOUNDS}
            overviews = [overview]
            details = [{"coverage": coverage, "title": title, "bounds_deg": region}
                       for coverage, (title, region) in MICHIGAN_SHARDS.items()]
        else:
            envelopes = [bounds]
            if bounds[2] > 180:
                points = tuple(_coordinates(feature["geometry"]["coordinates"]))
                envelopes = [(min(x for x, _ in points if x < 0), min(y for x, y in points if x < 0),
                              max(x for x, _ in points if x < 0), max(y for x, y in points if x < 0)),
                             (min(x for x, _ in points if x >= 0), min(y for x, y in points if x >= 0),
                              max(x for x, _ in points if x >= 0), max(y for x, y in points if x >= 0))]
            overviews = [{"coverage": f"us-{abbreviation.lower()}-overview" +
                          (f"-{index + 1}" if len(envelopes) > 1 else ""),
                          "bounds_deg": envelope}
                         for index, envelope in enumerate(envelopes)]
            overview = overviews[0]
            details = [region for index, envelope in enumerate(envelopes)
                       for region in _regions(envelope, abbreviation,
                                              f"{index + 1}-" if len(envelopes) > 1 else "")]
        states.append({"name": properties["NAME"], "abbreviation": abbreviation,
                       "fips": properties["GEOID"], "bounds_deg": bounds,
                       "overview": overview, "overview_regions": overviews,
                       "detail_shards": details})
    if len(states) != 50:
        raise ValueError("State map catalog requires exactly 50 states")
    return {"schema": 1, "kind": "state-map-build-catalog",
            "target_detail_spacing_m": 300, "states": states}


def state_plan(identifier):
    normalized = identifier.strip().lower()
    for state in catalog_document()["states"]:
        if normalized in (state["name"].lower(), state["abbreviation"].lower(), state["fips"]):
            return state
    raise ValueError(f"Unknown state: {identifier}")


def coverage_definition(coverage):
    for state in catalog_document()["states"]:
        for region in (*state["overview_regions"], *state["detail_shards"]):
            if region["coverage"] == coverage:
                return region.get("title", state["name"] + " overview"), tuple(region["bounds_deg"])
    raise ValueError(f"Unknown state coverage: {coverage}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state")
    parser.add_argument("--scope", choices=("overview", "detail", "all"), default="all")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--matrix", action="store_true")
    args = parser.parse_args()
    if args.state:
        state = state_plan(args.state)
        regions = (state["overview_regions"] if args.scope == "overview" else
                   state["detail_shards"] if args.scope == "detail" else
                   [*state["overview_regions"], *state["detail_shards"]])
        document = {"state": state["abbreviation"].lower(),
                    "coverage": [region["coverage"] for region in regions]} if args.matrix else state
    else:
        document = catalog_document()
    content = json.dumps(document, indent=None if args.matrix else 2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n")
    else:
        print(content)


if __name__ == "__main__":
    main()
