# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from protocols.map_renderer.map_renderer_client import (
    MapRendererClient,
    MapRendererUnavailableError,
)


def main() -> int:
    client = MapRendererClient()

    try:
        print("Moving camera to Detroit...")

        client.set_camera(
            latitude=42.3314,
            longitude=-83.0458,
            zoom=14.0,
            bearing=0.0,
            pitch=0.0,
        )

        print("Setting vehicle position to Detroit...")

        client.set_position(
            latitude=42.3314,
            longitude=-83.0458,
        )

    except MapRendererUnavailableError as exc:
        print(f"Map renderer unavailable: {exc}")
        return 1

    print("Commands sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
