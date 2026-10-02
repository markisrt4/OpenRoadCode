# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe live NOAA HRRR metadata and a raw reflectivity tile without the UI."""

import argparse
from pathlib import Path
from datetime import datetime, timezone

import requests

from controllers.weather.providers.hrrr_radar_provider import HrrrRadarProvider
from controllers.weather.hrrr_tiles import HrrrTileSource, color_hrrr_reflectivity
from controllers.weather.radar_tile_service import _UNIVERSAL_DBZ


def main():
    """Discover upcoming forecasts and save a tile over the central United States."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path.home() / ".cache/openroadcode/hrrr-forecast.png")
    args = parser.parse_args()
    provider = HrrrRadarProvider()
    frames = provider.get_frames()
    for frame in frames:
        print(f"Forecast valid UTC: {datetime.fromtimestamp(frame.timestamp, timezone.utc).isoformat()}")
    print(f"Selected model field: {frames[0].tile_url.split('?')[0]}")
    with requests.Session() as session:
        source = HrrrTileSource(Path.home() / ".cache/openroadcode/radar/hrrr-models", session)
        data = color_hrrr_reflectivity(source.tile(frames[0].tile_url, 4, 3, 6), _UNIVERSAL_DBZ)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"Validated raw reflectivity and saved PNG: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, requests.RequestException) as error:
        raise SystemExit(f"HRRR probe failed: {error}") from error
