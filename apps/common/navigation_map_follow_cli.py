# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Follow the normal OpenRoadCode navigation bus with the native map renderer."""

from __future__ import annotations

import argparse
import signal
import threading

from apps.common.navigation_map_follow import NavigationMapFollowRuntime
from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.map_renderer.map_position_adapter import MapPositionAdapter
from messaging.zeromq.subscriber import ZeroMqSubscriber
from protocols.map_renderer.map_renderer_client import MapRendererClient

DEFAULT_RUNTIME_CONFIG = "config/runtime.toml"
DEFAULT_RENDERER_ENDPOINT = "tcp://127.0.0.1:5562"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Follow published OpenRoadCode navigation position on MapLibre."
    )
    parser.add_argument("--config", default=DEFAULT_RUNTIME_CONFIG)
    parser.add_argument("--renderer-endpoint", default=DEFAULT_RENDERER_ENDPOINT)
    parser.add_argument("--no-follow", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = ServiceRuntimeConfigParser(args.config).load()
    stop_event = threading.Event()

    def stop(*_args) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    adapter = MapPositionAdapter(
        MapRendererClient(args.renderer_endpoint, timeout_ms=2000),
        follow=not args.no_follow,
    )
    runtime = NavigationMapFollowRuntime(
        ZeroMqSubscriber(config.messaging.subscriber_endpoint),
        adapter,
    )

    print(f"navigation bus: {config.messaging.subscriber_endpoint}")
    print(f"map renderer:   {args.renderer_endpoint}")
    print("waiting for navigation position; Ctrl+C to stop")

    try:
        runtime.start()
        stop_event.wait()
        return 0
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
