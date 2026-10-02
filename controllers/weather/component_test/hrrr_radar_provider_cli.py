# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe live NOAA HRRR metadata and a raw reflectivity tile without the UI."""

import argparse
from pathlib import Path
from datetime import datetime, timezone

import requests

from controllers.weather.providers.hrrr_radar_provider import HrrrRadarProvider
from controllers.weather.hrrr_tiles import HrrrTileSource, color_hrrr_reflectivity
from controllers.weather.hrrr_tiles import location_tile, reflectivity_summary
from controllers.cache import PersistentCache
from controllers.navigation.position_snapshot_cache import DEFAULT_POSITION_CACHE_DIRECTORY, PositionSnapshotCache
from controllers.weather.radar_tile_service import _UNIVERSAL_DBZ


def main():
    """Discover upcoming forecasts and save a tile over the central United States."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path.home() / ".cache/openroadcode/hrrr-forecast.png")
    parser.add_argument("--location", nargs=2, type=float, metavar=("LATITUDE", "LONGITUDE"),
                        help="Check a tile around these coordinates; defaults to cached GPS or central US")
    parser.add_argument("--frame", type=int, choices=range(1, 7), default=1,
                        help="Which upcoming hourly frame to check (1–6)")
    args = parser.parse_args()
    provider = HrrrRadarProvider()
    frames = provider.get_frames()
    for frame in frames:
        print(f"Forecast valid UTC: {datetime.fromtimestamp(frame.timestamp, timezone.utc).isoformat()}")
    frame = frames[args.frame - 1]
    print(f"Selected model field: {frame.tile_url.split('?')[0]}")
    location = args.location
    origin = "requested location"
    if location is None:
        position = PositionSnapshotCache(PersistentCache(DEFAULT_POSITION_CACHE_DIRECTORY)).load()
        if position is not None and position.has_fix and position.latitude_deg is not None and position.longitude_deg is not None:
            location = (position.latitude_deg, position.longitude_deg)
            origin = "cached GPS location"
    if location is None:
        tile = (4, 3, 6)
        print("Diagnostic area: central United States (no cached GPS; not a check of your location)")
    else:
        tile = location_tile(*location)
        print(f"Diagnostic area: {origin}, tile {tile[0]}/{tile[1]}/{tile[2]}")
    with requests.Session() as session:
        source = HrrrTileSource(Path.home() / ".cache/openroadcode/radar/hrrr-models", session)
        numeric = source.tile(frame.tile_url, *tile)
        summary = reflectivity_summary(numeric)
        if not summary["covered"]:
            raise RuntimeError("This tile has no usable model coverage; a blank image here does not mean clear weather")
        print(f"Model coverage: {summary['covered'] / summary['total']:.1%} of tile pixels")
        print(f"Visible reflectivity (>=5 dBZ): {summary['visible'] / summary['covered']:.1%} of covered pixels")
        print(f"Maximum reflectivity: {summary['max_dbz']:.1f} dBZ")
        if not summary["visible"]:
            print("Valid model data: no reflectivity above the map's display threshold in this tile")
        data = color_hrrr_reflectivity(numeric, _UNIVERSAL_DBZ)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"Validated raw reflectivity and saved PNG: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, requests.RequestException) as error:
        raise SystemExit(f"HRRR probe failed: {error}") from error
