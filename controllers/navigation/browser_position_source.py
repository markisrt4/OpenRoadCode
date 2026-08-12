# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Browser geolocation source with a small built-in HTTP relay."""

from __future__ import annotations

import json
import logging
import math
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.position_source_if import (
    PositionSourceIf,
    PositionStateCallback,
)


LOGGER = logging.getLogger(__name__)
_MAX_REQUEST_BYTES = 16_384

_LOCATION_PAGE = b"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OpenRoadCode Position</title>
  <style>
    body { background:#111; color:#eee; font:18px system-ui,sans-serif;
           max-width:42rem; margin:3rem auto; padding:0 1.5rem; }
    button { font:inherit; padding:.7rem 1rem; }
    #status { margin-top:1.5rem; white-space:pre-wrap; }
  </style>
</head>
<body>
  <h1>OpenRoadCode Position</h1>
  <p>This page sends this browser's location to the running Car UI.</p>
  <button id="start">Share location</button>
  <div id="status">Waiting to start.</div>
  <script>
    const status = document.querySelector('#status');
    let watchId = null;
    async function sendPosition(position) {
      const c = position.coords;
      const payload = {
        latitude: c.latitude, longitude: c.longitude,
        altitude: c.altitude, speed: c.speed, heading: c.heading,
        accuracy: c.accuracy
      };
      try {
        const response = await fetch('/position', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(await response.text());
        status.textContent = `Sharing ${c.latitude.toFixed(6)}, ${c.longitude.toFixed(6)}\nAccuracy: +/-${Math.round(c.accuracy)} m`;
      } catch (error) { status.textContent = `Relay error: ${error}`; }
    }
    document.querySelector('#start').addEventListener('click', () => {
      if (!navigator.geolocation) {
        status.textContent = 'Geolocation is not supported by this browser.';
        return;
      }
      if (watchId !== null) navigator.geolocation.clearWatch(watchId);
      status.textContent = 'Requesting location permission...';
      watchId = navigator.geolocation.watchPosition(
        sendPosition,
        error => { status.textContent = `Location error: ${error.message}`; },
        {enableHighAccuracy: true, maximumAge: 1000, timeout: 15000}
      );
    });
  </script>
</body>
</html>
"""


class BrowserPositionSource(PositionSourceIf):
    """Receive browser geolocation reports over a local HTTP endpoint."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self._host = host
        self._port = port
        self._callback: PositionStateCallback | None = None
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        """Return the configured or OS-assigned listening port."""
        server = self._server
        return server.server_port if server is not None else self._port

    @property
    def url(self) -> str:
        """Return the URL used by a browser on the same machine."""
        host = "localhost" if self._host in {"127.0.0.1", "::1"} else self._host
        return f"http://{host}:{self.port}/"

    def start(self, callback: PositionStateCallback) -> None:
        if self._server is not None:
            self._callback = callback
            return

        self._callback = callback
        source = self

        class RequestHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path not in {"/", "/index.html"}:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(_LOCATION_PAGE)))
                self.end_headers()
                self.wfile.write(_LOCATION_PAGE)

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/position":
                    self.send_error(404)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= _MAX_REQUEST_BYTES:
                        raise ValueError("invalid request size")
                    payload = json.loads(self.rfile.read(length))
                    state = source._state_from_payload(payload)
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    self.send_error(400, str(exc))
                    return

                callback = source._callback
                if callback is not None:
                    callback(state)
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                LOGGER.debug("Browser position relay: " + format, *args)

        try:
            self._server = ThreadingHTTPServer((self._host, self._port), RequestHandler)
        except Exception:
            self._callback = None
            raise
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="browser-position-source",
            daemon=True,
        )
        self._thread.start()
        LOGGER.info("Browser position page available at %s", self.url)
        print(f"[Position] Open {self.url} and select 'Share location'")

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        self._callback = None
        self._server = None
        self._thread = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    @staticmethod
    def _state_from_payload(payload: Any) -> PositionState:
        if not isinstance(payload, dict):
            raise ValueError("position must be a JSON object")
        latitude = _number(payload.get("latitude"), "latitude", required=True)
        longitude = _number(payload.get("longitude"), "longitude", required=True)
        assert latitude is not None and longitude is not None
        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return PositionState(
            latitude_deg=latitude,
            longitude_deg=longitude,
            altitude_m=_number(payload.get("altitude"), "altitude"),
            speed_mps=_number(payload.get("speed"), "speed"),
            course_deg=_number(payload.get("heading"), "heading"),
            accuracy_m=_number(payload.get("accuracy"), "accuracy"),
            fix_mode=3,
            source="browser",
        )


def _number(value: Any, name: str, *, required: bool = False) -> float | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result
