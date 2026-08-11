"""Component test for the native map renderer client."""

from protocols.map_renderer.map_renderer_client import (
    MapRendererClient,
    MapRendererUnavailableError,
)


def main() -> int:
    client = MapRendererClient()

    print("Moving map to Detroit...")

    try:
        client.set_center(
            latitude=42.3314,
            longitude=-83.0458,
        )
    except MapRendererUnavailableError as exc:
        print(f"Map renderer unavailable: {exc}")
        return 1

    print("Command sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
