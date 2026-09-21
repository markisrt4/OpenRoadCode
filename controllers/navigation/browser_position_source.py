# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""HTTP browser-geolocation position source with optional route simulation."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from controllers.navigation.browser_position_adapter import BrowserPositionAdapter
from controllers.navigation.position_source_if import PositionSourceIf, PositionStateCallback
from controllers.navigation.route_simulation_if import RouteSimulationIf
from controllers.navigation.simulated_position_source import SimulatedPositionSource
from controllers.route_planning.route_planning_types import RouteResult

_MAX_REQUEST_BYTES = 16_384
_LOCATION_PAGE = b"""<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><title>OpenRoadCode Position</title><body><h1>OpenRoadCode Position</h1><button id=start>Share location</button><pre id=status>Waiting to start.</pre><script>const s=document.querySelector('#status');document.querySelector('#start').onclick=()=>navigator.geolocation.watchPosition(async p=>{const c=p.coords;const r=await fetch('/position',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({latitude:c.latitude,longitude:c.longitude,altitude:c.altitude,speed:c.speed,heading:c.heading,accuracy:c.accuracy})});s.textContent=r.ok?`${c.latitude.toFixed(6)}, ${c.longitude.toFixed(6)}`:await r.text();},e=>s.textContent=e.message,{enableHighAccuracy:true,maximumAge:1000,timeout:15000});</script></body>"""


class _BrowserPositionHttpServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class BrowserPositionSource(PositionSourceIf, RouteSimulationIf):
    """Receive browser geolocation and allow an active route to take over position."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self._host = host
        self._port = port
        self._callback: PositionStateCallback | None = None
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._route_simulator = SimulatedPositionSource(profile="stationary")
        self._route_simulating = False
        self._lock = threading.Lock()

    @property
    def port(self) -> int:
        return self._server.server_port if self._server is not None else self._port

    @property
    def url(self) -> str:
        host = "localhost" if self._host in {"127.0.0.1", "::1"} else self._host
        return f"http://{host}:{self.port}/"

    def start(self, callback: PositionStateCallback) -> None:
        if self._server is not None:
            self._callback = callback
            return
        self._callback = callback
        source = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path not in {"/", "/index.html"}:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(_LOCATION_PAGE)

            def do_POST(self) -> None:
                if self.path != "/position":
                    self.send_error(404)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= _MAX_REQUEST_BYTES:
                        raise ValueError("invalid request size")
                    state = BrowserPositionAdapter.state_from_payload(
                        json.loads(self.rfile.read(length))
                    )
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    self.send_error(400, str(exc))
                    return
                with source._lock:
                    callback_now = source._callback
                    route_simulating = source._route_simulating
                if callback_now is not None and not route_simulating:
                    callback_now(state)
                self.send_response(204)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                pass

        try:
            self._server = _BrowserPositionHttpServer((self._host, self._port), Handler)
        except Exception:
            self._callback = None
            raise
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="browser-position",
            daemon=True,
        )
        self._thread.start()
        print(f"[Position] Open {self.url} and select 'Share location'")

    def stop(self) -> None:
        self._route_simulator.stop()
        server, thread = self._server, self._thread
        with self._lock:
            self._callback = None
            self._route_simulating = False
        self._server = None
        self._thread = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def follow_route(self, route: RouteResult, *, time_scale: float = 60.0) -> None:
        """Temporarily replace browser reports with positions along the active route."""
        with self._lock:
            callback = self._callback
            self._route_simulating = True
        if callback is None:
            with self._lock:
                self._route_simulating = False
            raise RuntimeError("browser position source is not running")
        try:
            self._route_simulator.follow_route(route, time_scale=time_scale)
            self._route_simulator.start(callback)
        except Exception:
            with self._lock:
                self._route_simulating = False
            raise

    def stop_route(self) -> None:
        """Stop route simulation and resume live browser geolocation reports."""
        self._route_simulator.stop()
        self._route_simulator.stop_route()
        with self._lock:
            self._route_simulating = False
