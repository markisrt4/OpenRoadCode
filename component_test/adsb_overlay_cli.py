# SPDX-License-Identifier: MIT
"""Publish simulated aircraft to ORC's native map renderer.

Run from the repository root: python -m component_test.adsb_overlay_cli
"""

import argparse
import time
from controllers.adsb.aircraft_overlay_controller import AircraftOverlayController
from controllers.adsb.aircraft_snapshot_adapter import aircraft_from_snapshot
from frontends.common.map_aircraft_overlay_ui import MapAircraftOverlayUi
from protocols.map_renderer.map_renderer_client import MapRendererClient


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulate aircraft on the native ORC map")
    parser.add_argument("--source", choices=("simulated",), default="simulated")
    parser.add_argument("--aircraft", type=int, default=10)
    parser.add_argument("--update-hz", type=float, default=2.0)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--latitude", type=float, default=42.5)
    parser.add_argument("--longitude", type=float, default=-83.0)
    parser.add_argument("--endpoint", help="Override ZeroMQ publisher endpoint")
    args = parser.parse_args(argv)
    if args.aircraft < 0 or args.update_hz <= 0 or args.duration < 0:
        parser.error("aircraft must be >= 0, update-hz > 0, duration >= 0")
    if not -90 < args.latitude < 90 or not -180 <= args.longitude <= 180:
        parser.error("invalid center latitude/longitude")

    try:
        from sdrforge.adsb.simulation import simulated_aircraft
    except ImportError as exc:
        parser.error("Install libSDRForge in this environment: pip install -e ../libSDRForge")

    with_client = MapRendererClient(endpoint=args.endpoint)
    try:
        controller = AircraftOverlayController(MapAircraftOverlayUi(with_client))
        start = time.monotonic()
        interval = 1.0 / args.update_hz
        next_tick = start
        while time.monotonic() - start < args.duration:
            now = time.monotonic()
            if now < next_tick:
                time.sleep(next_tick - now)
                continue
            elapsed = now - start
            snapshot = simulated_aircraft(
                elapsed,
                args.aircraft,
                center_lat=args.latitude,
                center_lon=args.longitude,
            )
            controller.set_aircraft(aircraft_from_snapshot(snapshot))
            print(f"t={elapsed:6.1f}s aircraft={len(snapshot)}", flush=True)
            next_tick += interval
            if next_tick < now:
                next_tick = now + interval
    except KeyboardInterrupt:
        print("Interrupted, clearing aircraft overlay")
    finally:
        controller.set_aircraft(())
        with_client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
