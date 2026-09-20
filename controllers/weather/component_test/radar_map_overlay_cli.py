# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Live radar-to-native-map component test."""

from __future__ import annotations

import argparse
import time

from controllers.weather.providers import RainViewerRadarProvider
from protocols.map_renderer.map_renderer_client import MapRendererClient


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the latest RainViewer frame through the native map renderer"
    )
    parser.add_argument("--opacity", type=float, default=0.65)
    parser.add_argument(
        "--seconds",
        type=float,
        default=15.0,
        help="Seconds to leave radar visible before hiding it",
    )
    args = parser.parse_args()

    frame = RainViewerRadarProvider().get_frames()[-1]
    client = MapRendererClient()
    try:
        client.set_weather_radar(
            frame.tile_url,
            frame_time=frame.timestamp,
            opacity=args.opacity,
        )
        print(f"Radar frame {frame.timestamp} published; visible for {args.seconds:g}s")
        time.sleep(max(0.0, args.seconds))
        client.set_weather_radar(None, enabled=False, opacity=args.opacity)
        print("Radar overlay hidden")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
