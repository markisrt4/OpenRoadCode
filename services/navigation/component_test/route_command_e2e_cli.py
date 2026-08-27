# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise route calculation through HTTP, controller, service, and ZeroMQ."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import zmq

from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from protocols.valhalla.valhalla_http_client import ValhallaHttpClient
from services.navigation.navigation_command_service import (
    CALCULATE_ROUTE_COMMAND,
    NavigationCommandService,
)
from services.navigation.zeromq_navigation_command_server import (
    ZeroMqNavigationCommandServer,
)

VALHALLA_HOST = "127.0.0.1"
VALHALLA_PORT = 18002
COMMAND_ENDPOINT = "tcp://127.0.0.1:15560"


class _UnusedNavigationController:
    """Minimal placeholder because this component test exercises routing only."""


class _FakeValhallaHandler(BaseHTTPRequestHandler):
    """Serve the small subset of Valhalla used by the route planner."""

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/status":
            self.send_error(404)
            return
        self._send_json({"version": "component-test"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/route":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length) or b"{}")
        locations = request.get("locations", [])
        if len(locations) != 2:
            self._send_json({"error": "two locations required"}, status=400)
            return

        self._send_json(
            {
                "trip": {
                    "summary": {
                        "length": 42.5,
                        "time": 3600.0,
                    },
                    "legs": [
                        {
                            "maneuvers": [
                                {
                                    "instruction": "Head south",
                                    "verbal_pre_transition_instruction": "Head south",
                                    "length": 1.0,
                                    "time": 120.0,
                                    "begin_shape_index": 0,
                                    "end_shape_index": 1,
                                },
                                {
                                    "instruction": "Arrive at destination",
                                    "length": 0.0,
                                    "time": 0.0,
                                    "begin_shape_index": 1,
                                    "end_shape_index": 1,
                                },
                            ]
                        }
                    ],
                }
            }
        )

    def log_message(self, format: str, *args) -> None:
        """Keep component-test output focused on the integration result."""

    def _send_json(self, payload: object, *, status: int = 200) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _wait_for_command_server(server: ZeroMqNavigationCommandServer) -> None:
    deadline = time.monotonic() + 2.0
    while not server.is_running:
        if time.monotonic() >= deadline:
            raise RuntimeError("ZeroMQ navigation command server did not start")
        time.sleep(0.01)


def main() -> int:
    http_server = ThreadingHTTPServer(
        (VALHALLA_HOST, VALHALLA_PORT),
        _FakeValhallaHandler,
    )
    http_thread = threading.Thread(
        target=http_server.serve_forever,
        name="fake-valhalla",
        daemon=True,
    )
    http_thread.start()

    route_planner = ValhallaRoutePlanningController(
        ValhallaHttpClient(
            f"http://{VALHALLA_HOST}:{VALHALLA_PORT}",
            timeout_seconds=2.0,
        )
    )
    service = NavigationCommandService(
        _UnusedNavigationController(),
        route_planning_controller=route_planner,
    )
    command_server = ZeroMqNavigationCommandServer(
        service,
        COMMAND_ENDPOINT,
    )
    command_thread = threading.Thread(
        target=command_server.run,
        name="navigation-command-component-test",
        daemon=True,
    )
    command_thread.start()

    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 2000)
    socket.setsockopt(zmq.SNDTIMEO, 2000)

    try:
        _wait_for_command_server(command_server)
        socket.connect(COMMAND_ENDPOINT)
        socket.send_json(
            {
                "command": CALCULATE_ROUTE_COMMAND,
                "arguments": {
                    "origin": {
                        "latitude": 42.8028,
                        "longitude": -83.0127,
                    },
                    "destination": {
                        "latitude": 42.3314,
                        "longitude": -83.0458,
                    },
                    "travel_mode": "AUTO",
                },
            }
        )
        response = socket.recv_json()

        if not response.get("ok"):
            raise RuntimeError(f"Route command failed: {response}")

        data = response.get("data")
        if not isinstance(data, dict):
            raise RuntimeError(f"Route command returned no data: {response}")

        print("Navigation route component test passed")
        print(f"  distance:  {data['distance_miles']} miles")
        print(f"  duration:  {data['duration_seconds']} seconds")
        print(f"  maneuvers: {len(data['maneuvers'])}")
        print(f"  first:     {data['maneuvers'][0]['instruction']}")
        return 0
    finally:
        socket.close(linger=0)
        context.term()
        command_server.close()
        command_thread.join(timeout=1.0)
        http_server.shutdown()
        http_server.server_close()
        http_thread.join(timeout=1.0)


if __name__ == "__main__":
    raise SystemExit(main())
