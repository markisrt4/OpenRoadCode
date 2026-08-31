# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise routing through navigation commands and map presentation."""

from __future__ import annotations

import argparse
import json
import threading
import time
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from controllers.route_planning.route_map_presenter import present_route
from controllers.route_planning.route_planning_types import GeoPoint, RouteRequest
from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from messaging.publisher_if import PublisherIf
from protocols.map_renderer.map_renderer_client import MapRendererClient
from protocols.map_renderer.map_renderer_protocol import MAP_RENDERER_COMMAND_TOPIC
from protocols.valhalla.valhalla_http_client import ValhallaHttpClient
from services.navigation.navigation_command_client import NavigationCommandClient
from services.navigation.navigation_command_service import NavigationCommandService
from services.navigation.zeromq_navigation_command_server import (
    ZeroMqNavigationCommandServer,
)

VALHALLA_PORT = 18003
DEFAULT_EXTERNAL_VALHALLA_URL = "http://127.0.0.1:8002"
NAV_ENDPOINT = "tcp://127.0.0.1:15561"

# Deterministic Michigan test geometry. Keep the fake route inside the map
# dataset so an external renderer can fit the route and still display a
# meaningful basemap.
MICHIGAN_TEST_SHAPE = "_fnspAvdui}C~liHfgM~}cH~oRnhhInz]"


class _UnusedNavigationController:
    pass


class _FakeValhallaHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/status":
            self._reply({"version": "component-test"})
        else:
            self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/route":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length) or b"{}")
        if len(request.get("locations", [])) != 2:
            self._reply({"error": "two locations required"}, 400)
            return

        self._reply(
            {
                "trip": {
                    "summary": {"length": 33.0, "time": 2700.0},
                    "legs": [
                        {
                            "shape": MICHIGAN_TEST_SHAPE,
                            "maneuvers": [
                                {
                                    "instruction": "Head south toward Detroit",
                                    "verbal_pre_transition_instruction": "Head south toward Detroit",
                                    "length": 33.0,
                                    "time": 2700.0,
                                    "begin_shape_index": 0,
                                    "end_shape_index": 3,
                                }
                            ],
                        }
                    ],
                }
            }
        )

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _reply(self, payload: object, status: int = 200) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class _RecordingPublisher(PublisherIf):
    """Capture renderer messages without requiring a native renderer."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []

    def publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        self.messages.append((topic, dict(payload)))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--external-renderer",
        action="store_true",
        help="publish map commands through the running OpenRoadCode broker",
    )
    parser.add_argument(
        "--external-valhalla",
        action="store_true",
        help="use a running Valhalla service instead of the fake HTTP server",
    )
    parser.add_argument(
        "--valhalla-url",
        default=DEFAULT_EXTERNAL_VALHALLA_URL,
        help=(
            "external Valhalla base URL; used with --external-valhalla "
            f"(default: {DEFAULT_EXTERNAL_VALHALLA_URL})"
        ),
    )
    return parser.parse_args()


def _wait_navigation(server: ZeroMqNavigationCommandServer) -> None:
    deadline = time.monotonic() + 2.0
    while not server.is_running:
        if time.monotonic() >= deadline:
            raise RuntimeError("Navigation command server did not start")
        time.sleep(0.01)


def main() -> int:
    args = _parse_args()

    http_server: ThreadingHTTPServer | None = None
    http_thread: threading.Thread | None = None
    if args.external_valhalla:
        valhalla_url = args.valhalla_url
    else:
        http_server = ThreadingHTTPServer(
            ("127.0.0.1", VALHALLA_PORT),
            _FakeValhallaHandler,
        )
        http_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        http_thread.start()
        valhalla_url = f"http://127.0.0.1:{VALHALLA_PORT}"

    planner = ValhallaRoutePlanningController(
        ValhallaHttpClient(valhalla_url, timeout_seconds=2.0)
    )
    navigation_server = ZeroMqNavigationCommandServer(
        NavigationCommandService(
            _UnusedNavigationController(),
            route_planning_controller=planner,
        ),
        NAV_ENDPOINT,
    )
    navigation_thread = threading.Thread(target=navigation_server.run, daemon=True)
    navigation_thread.start()

    recording_publisher: _RecordingPublisher | None = None
    if args.external_renderer:
        map_renderer = MapRendererClient()
        renderer_description = "OpenRoadCode broker map.command topic"
    else:
        recording_publisher = _RecordingPublisher()
        map_renderer = MapRendererClient(recording_publisher)
        renderer_description = "recording publisher"

    try:
        _wait_navigation(navigation_server)
        route = NavigationCommandClient(NAV_ENDPOINT).calculate_route(
            RouteRequest(
                origin=GeoPoint(42.8028, -83.0127),
                destination=GeoPoint(42.3314, -83.0458),
            )
        )
        present_route(route, map_renderer)
        map_renderer.close()

        if recording_publisher is not None:
            topics = [topic for topic, _ in recording_publisher.messages]
            commands = [payload.get("command") for _, payload in recording_publisher.messages]
            if topics != [MAP_RENDERER_COMMAND_TOPIC, MAP_RENDERER_COMMAND_TOPIC]:
                raise RuntimeError(f"Unexpected renderer topics: {topics!r}")
            if commands != ["set_route", "fit_bounds"]:
                raise RuntimeError(
                    f"Unexpected renderer commands: {recording_publisher.messages!r}"
                )

        print("Route-to-map component test passed")
        print(f"  route distance: {route.distance_miles} miles")
        print(f"  route points:   {len(route.shape)}")
        print(f"  valhalla:       {valhalla_url}")
        print(f"  renderer:       {renderer_description}")
        print("  commands:       set_route -> fit_bounds")
        return 0
    finally:
        map_renderer.close()
        navigation_server.close()
        navigation_thread.join(1.0)
        if http_server is not None:
            http_server.shutdown()
            http_server.server_close()
        if http_thread is not None:
            http_thread.join(1.0)


if __name__ == "__main__":
    raise SystemExit(main())
