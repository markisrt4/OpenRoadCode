# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Live RainViewer radar-provider component test."""

from __future__ import annotations

from datetime import datetime, timezone

from controllers.weather.providers import RainViewerRadarProvider


def main() -> int:
    frames = RainViewerRadarProvider().get_frames()
    latest = frames[-1]

    print("OpenRoadCode Radar Provider Component Test")
    print("Provider: rainviewer")
    print(f"Frames: {len(frames)}")
    print(
        "Latest: "
        f"{datetime.fromtimestamp(latest.timestamp, tz=timezone.utc).isoformat()}"
    )
    print(f"Tile template: {latest.tile_url}")

    if "{z}" not in latest.tile_url or "{x}" not in latest.tile_url or "{y}" not in latest.tile_url:
        raise RuntimeError("Provider returned a non-XYZ radar tile template")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
