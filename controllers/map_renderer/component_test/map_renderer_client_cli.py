"""Exercise the native map renderer client."""

from controllers.map_renderer.map_renderer_client import (
    MapRendererClient,
)


def main() -> None:
    client = MapRendererClient()

    client.set_center(
        latitude=42.3314,
        longitude=-83.0458,
    )

if __name__ == "__main__":
    main()
