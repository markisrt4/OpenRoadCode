# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Follow the normal OpenRoadCode navigation bus with the native map renderer."""

from __future__ import annotations

import argparse
import select
import signal
import sys
import termios
import threading
import tty

from apps.common.navigation_map_follow import NavigationMapFollowRuntime
from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.map_renderer.map_position_adapter import MapPositionAdapter
from messaging.zeromq.publisher import ZeroMqPublisher
from messaging.zeromq.subscriber import ZeroMqSubscriber
from protocols.map_renderer.map_renderer_client import MapRendererClient

DEFAULT_RUNTIME_CONFIG = "config/runtime.toml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Follow published OpenRoadCode navigation position on MapLibre."
    )
    parser.add_argument("--config", default=DEFAULT_RUNTIME_CONFIG)
    parser.add_argument("--no-follow", action="store_true")
    return parser.parse_args()


def _run_camera_controls(adapter: MapPositionAdapter, stop_event: threading.Event) -> None:
    if not sys.stdin.isatty():
        return

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while not stop_event.is_set():
            ready, _, _ = select.select([sys.stdin], [], [], 0.2)
            if not ready:
                continue
            key = sys.stdin.read(1).lower()
            if key in ("q", "\x03"):
                stop_event.set()
                continue
            if key in ("+", "="):
                camera = adapter.adjust_camera(zoom_delta=0.5)
            elif key in ("-", "_"):
                camera = adapter.adjust_camera(zoom_delta=-0.5)
            elif key == "w":
                camera = adapter.adjust_camera(pitch_delta=5.0)
            elif key == "s":
                camera = adapter.adjust_camera(pitch_delta=-5.0)
            elif key == "a":
                camera = adapter.adjust_camera(bearing_delta=-10.0)
            elif key == "d":
                camera = adapter.adjust_camera(bearing_delta=10.0)
            elif key == "r":
                adapter.enable_auto_camera()
                print("\r[camera] AUTO speed-aware zoom / course bearing          ")
                continue
            else:
                continue

            zoom, pitch, bearing = camera
            print(
                f"\r[camera] MANUAL zoom={zoom:.1f} pitch={pitch:.0f} "
                f"bearing={bearing:.0f}          "
            )
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)


def main() -> int:
    args = _parse_args()
    config = ServiceRuntimeConfigParser(args.config).load()
    stop_event = threading.Event()

    def stop(*_args) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    adapter = MapPositionAdapter(
        MapRendererClient(
            ZeroMqPublisher(config.messaging.publisher_endpoint)
        ),
        follow=not args.no_follow,
    )
    runtime = NavigationMapFollowRuntime(
        ZeroMqSubscriber(config.messaging.subscriber_endpoint),
        adapter,
    )

    print(f"navigation bus: {config.messaging.subscriber_endpoint}")
    print(f"map commands:   {config.messaging.publisher_endpoint} topic=map.command")
    print("camera: AUTO speed-aware zoom / course bearing")
    print("controls: +/- zoom | W/S pitch | A/D bearing | R auto | Q quit")
    print("waiting for navigation position")

    controls_thread: threading.Thread | None = None
    try:
        runtime.start()
        if sys.stdin.isatty() and not args.no_follow:
            controls_thread = threading.Thread(
                target=_run_camera_controls,
                args=(adapter, stop_event),
                name="NavigationMapCameraControls",
                daemon=True,
            )
            controls_thread.start()
        stop_event.wait()
        return 0
    finally:
        stop_event.set()
        if controls_thread is not None and controls_thread.is_alive():
            controls_thread.join(timeout=0.5)
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
