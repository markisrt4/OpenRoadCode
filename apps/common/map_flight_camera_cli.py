# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Keyboard-driven free-flight experiment for the native MapLibre renderer."""

from __future__ import annotations

import argparse
import select
import signal
import sys
import termios
import threading
import tty

from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.map_renderer.flight_camera_controller import FlightCameraController, FlightState
from messaging.zeromq.publisher import ZeroMqPublisher
from protocols.map_renderer.map_renderer_client import MapRendererClient

DEFAULT_RUNTIME_CONFIG = "config/runtime.toml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fly a virtual camera over the OpenRoadCode MapLibre map.")
    parser.add_argument("--config", default=DEFAULT_RUNTIME_CONFIG)
    parser.add_argument("--latitude", type=float, default=42.8028)
    parser.add_argument("--longitude", type=float, default=-83.0127)
    parser.add_argument("--heading", type=float, default=180.0)
    parser.add_argument("--speed-mps", type=float, default=25.0)
    parser.add_argument("--zoom", type=float, default=14.0)
    parser.add_argument("--pitch", type=float, default=55.0)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = ServiceRuntimeConfigParser(args.config).load()
    stop_event = threading.Event()

    def stop(*_args) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    renderer = MapRendererClient(ZeroMqPublisher(config.messaging.publisher_endpoint))
    controller = FlightCameraController(
        renderer,
        FlightState(
            latitude_deg=args.latitude,
            longitude_deg=args.longitude,
            heading_deg=args.heading,
            speed_mps=args.speed_mps,
            zoom=args.zoom,
            pitch_deg=args.pitch,
        ),
    )

    print(f"map commands: {config.messaging.publisher_endpoint} topic=map.command")
    print("flight controls: W/S throttle | A/D turn | I/K pitch | +/- altitude/zoom | SPACE stop | Q quit")

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd) if sys.stdin.isatty() else None
    try:
        controller.start()
        if previous is None:
            stop_event.wait()
            return 0
        tty.setcbreak(fd)
        while not stop_event.is_set():
            ready, _, _ = select.select([sys.stdin], [], [], 0.2)
            if not ready:
                continue
            key = sys.stdin.read(1).lower()
            if key in ("q", "\x03"):
                break
            if key == "w":
                state = controller.adjust(speed_delta_mps=5.0)
            elif key == "s":
                state = controller.adjust(speed_delta_mps=-5.0)
            elif key == "a":
                state = controller.adjust(heading_delta_deg=-5.0)
            elif key == "d":
                state = controller.adjust(heading_delta_deg=5.0)
            elif key == "i":
                state = controller.adjust(pitch_delta_deg=5.0)
            elif key == "k":
                state = controller.adjust(pitch_delta_deg=-5.0)
            elif key in ("+", "="):
                state = controller.adjust(zoom_delta=0.5)
            elif key in ("-", "_"):
                state = controller.adjust(zoom_delta=-0.5)
            elif key == " ":
                state = controller.state
                state = controller.adjust(speed_delta_mps=-state.speed_mps)
            else:
                continue
            print(
                f"\rflight lat={state.latitude_deg:.5f} lon={state.longitude_deg:.5f} "
                f"hdg={state.heading_deg:05.1f} speed={state.speed_mps:5.1f}m/s "
                f"pitch={state.pitch_deg:4.0f} zoom={state.zoom:4.1f}      ",
                end="",
                flush=True,
            )
        return 0
    finally:
        stop_event.set()
        controller.stop()
        renderer.close()
        if previous is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, previous)
        print()


if __name__ == "__main__":
    raise SystemExit(main())
