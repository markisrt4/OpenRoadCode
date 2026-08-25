# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise routing through navigation commands and map presentation."""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import zmq

from controllers.route_planning.route_map_presenter import present_route
from controllers.route_planning.route_planning_types import GeoPoint, RouteRequest
from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from protocols.map_renderer.map_renderer_client import (
    DEFAULT_MAP_RENDERER_ENDPOINT,
    MapRendererClient,
)
from protocols.valhalla.valhalla_http_client import ValhallaHttpClient
from services.navigation.navigation_command_client import NavigationCommandClient
from services.navigation.navigation_command_service import NavigationCommandService
from services.navigation.zeromq_navigation_command_server import (
    ZeroMqNavigationCommandServer,
)

VALHALLA_PORT = 18003
DEFAULT_EXTERNAL_VALHALLA_URL = "http://127.0.0.1:8002"
NAV_ENDPOINT = "tcp://127.0.0.1:15561"
FAKE_MAP_ENDPOINT = "tcp://127.0.0.1:15562"

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
                                    "verbal_pre_transition_instruction": (
                                        "Head south toward Detroit"
                                    ),
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

    def log_message(self, format: str, *args) -> None:
        pass

    def _reply(self, payload: object, status: int = 200) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class _FakeMapRenderer:
    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        self.commands: list[dict[str, object]] = []
        self._stop = threading.Event()
        self._running = threading.Event()

    def run(self) -> None:
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 100)
        socket.bind(self._endpoint)
        self._running.set()
        try:
            while not self._stop.is_set():
                try:
                    command = socket.recv_json()
                except zmq.Again:
                    continue
                self.commands.append(command)
                socket.send_json({"ok": True})
        finally:
            self._running.clear()
            socket.close(0)
            context.term()

    def wait_until_running(self) -> None:
        if not self._running.wait(2.0):
            raise RuntimeError("Fake map renderer did not start")

    def close(self) -> None:
        self._stop.set()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--external-renderer",
        action="store_true",
        help="send map commands to a running native renderer",
    )
    parser.add_argument(
        "--renderer-endpoint",
        default=None,
        help=(
            "renderer ZeroMQ endpoint; defaults to the native IPC endpoint "
            "with --external-renderer and the test TCP endpoint otherwise"
        ),
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
    renderer_endpoint = args.renderer_endpoint or (
        DEFAULT_MAP_RENDERER_ENDPOINT
        if args.external_renderer
        else FAKE_MAP_ENDPOINT
    )

    http_server: ThreadingHTTPServer | None = None
    http_thread: threading.Thread | None = None
    if args.external_valhalla:
        valhalla_url = args.valhalla_url
    else:
        http_server = ThreadingHTTPServer(
            ("127.0.0.1", VALHALLA_PORT),
            _FakeValhallaHandler,
        )
        http_thread = threading.Thread(
            target=http_server.serve_forever,
            daemon=True,
        )
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
    navigation_thread = threading.Thread(
        target=navigation_server.run,
        daemon=True,
    )
    navigation_thread.start()

    fake_renderer = None
    renderer_thread = None
    if not args.external_renderer:
        fake_renderer = _FakeMapRenderer(renderer_endpoint)
        renderer_thread = threading.Thread(
            target=fake_renderer.run,
            daemon=True,
        )
        renderer_thread.start()

    try:
        _wait_navigation(navigation_server)
        if fake_renderer is not None:
            fake_renderer.wait_until_running()

        route = NavigationCommandClient(NAV_ENDPOINT).calculate_route(
            RouteRequest(
                origin=GeoPoint(42.8028, -83.0127),
                destination=GeoPoint(42.3314, -83.0458),
            )
        )
        present_route(route, MapRendererClient(renderer_endpoint))

        if fake_renderer is not None:
            commands = [item.get("command") for item in fake_renderer.commands]
            if commands != ["set_route", "fit_bounds"]:
                raise RuntimeError(
                    f"Unexpected renderer commands: {fake_renderer.commands!r}"
                )

        print("Route-to-map component test passed")
        print(f"  route distance: {route.distance_miles} miles")
        print(f"  route points:   {len(route.shape)}")
        print(f"  valhalla:       {valhalla_url}")
        print(f"  renderer:       {renderer_endpoint}")
        print("  commands:       set_route -> fit_bounds")
        return 0
    finally:
        navigation_server.close()
        navigation_thread.join(1.0)
        if fake_renderer is not None:
            fake_renderer.close()
        if renderer_thread is not None:
            renderer_thread.join(1.0)
        if http_server is not None:
            http_server.shutdown()
            http_server.server_close()
        if http_thread is not None:
            http_thread.join(1.0)


if __name__ == "__main__":
    raise SystemExit(main())
