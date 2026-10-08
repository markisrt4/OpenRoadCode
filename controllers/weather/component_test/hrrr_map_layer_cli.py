# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Probe a real HRRR model heatmap through the local HTTP tile pipeline."""

import argparse
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image
import requests

from controllers.weather.hrrr_map_layers import HrrrMapLayerProvider
from controllers.weather.hrrr_tiles import location_tile
from controllers.weather.radar_palette import RadarPalette
from controllers.weather.radar_tile_service import RadarTileService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('temperature', 'wind'), required=True)
    parser.add_argument('--location', nargs=2, type=float, required=True, metavar=('LAT', 'LON'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    provider = HrrrMapLayerProvider()
    service = None
    try:
        frame = provider.get_frame(args.kind)
        z, x, y = location_tile(*args.location)
        service = RadarTileService()
        url = service.tile_url(frame, RadarPalette.UNIVERSAL).format(z=z, x=x, y=y)
        response = requests.get(url, timeout=180)
        response.raise_for_status()
        with Image.open(BytesIO(response.content)) as image:
            image = image.convert('RGBA')
            covered = sum(image.getchannel('A').histogram()[1:])
            print(f'Model coverage: {covered / (image.width * image.height):.1%} of tile pixels')
        output = args.output or Path.home() / f'.cache/openroadcode/hrrr-{args.kind}.png'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(response.content)
        print('Layer:', args.kind)
        print('Forecast valid UTC:', datetime.fromtimestamp(frame.timestamp, timezone.utc).isoformat())
        print(f'Diagnostic tile: {z}/{x}/{y}')
        print('Saved:', output)
    except Exception as error:
        parser.exit(1, f'HRRR map layer probe failed: {error}\n')
    finally:
        provider.close()
        if service is not None:
            service.close()


if __name__ == '__main__':
    main()
