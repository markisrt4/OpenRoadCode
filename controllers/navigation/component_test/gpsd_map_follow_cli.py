"""Follow a live gpsd position in the native map renderer."""

from __future__ import annotations

import argparse
import logging
import time

from controllers.navigation import GpsdPositionSource
from controllers.map_renderer.map_position_adapter import MapPositionAdapter
from protocols.map_renderer.map_renderer_client import MapRendererClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display and follow live gpsd fixes on the native map.",
    )
    parser.add_argument("--gps-host", default="127.0.0.1")
    parser.add_argument("--gps-port", default="2947")
    parser.add_argument(
        "--socket",
        default="/tmp/openroadcode-map-renderer.sock",
        help="Map renderer Unix socket path.",
    )
    parser.add_argument("--zoom", type=float, default=16.5)
    parser.add_argument("--pitch", type=float, default=45.0)
    parser.add_argument(
        "--camera-interval",
        type=float,
        default=0.25,
        help="Minimum seconds between follow-camera updates.",
    )
    parser.add_argument(
        "--course-speed",
        type=float,
        default=1.0,
        help="Minimum m/s before GPS course rotates the map.",
    )
    parser.add_argument(
        "--no-follow",
        action="store_true",
        help="Move only the vehicle marker; leave the camera untouched.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from hardware_io.gps import GpsReader

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    source = GpsdPositionSource(
        GpsReader(host=args.gps_host, port=args.gps_port),
    )
    adapter = MapPositionAdapter(
        MapRendererClient(socket_path=args.socket),
        follow=not args.no_follow,
        zoom=args.zoom,
        pitch=args.pitch,
        minimum_camera_interval_s=args.camera_interval,
        minimum_course_speed_mps=args.course_speed,
    )

    print(f"Connecting to gpsd at {args.gps_host}:{args.gps_port}...")
    print(f"Sending live fixes to {args.socket}")
    print("Waiting for a 2D/3D fix. Press Ctrl+C to stop.")

    try:
        source.start(adapter.update)
        while True:
            time.sleep(1.0)
    except (ConnectionRefusedError, OSError) as error:
        print(f"Unable to start live map following: {error}")
        return 1
    except KeyboardInterrupt:
        print("\nStopping live map following...")
    finally:
        source.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
