# SPDX-License-Identifier: MIT
"""Exercise REST recovery across a real localhost server restart, without SDR hardware."""

from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from controllers.radio.adapters.sdrforge_rest_radio_backend import SdrForgeRestRadioBackend


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/health":
            payload = {"status": "ok"}
        elif self.path == "/v1/receiver":
            payload = {"frequency_hz": 94700000, "source_type": "simulated"}
        else:
            self.send_error(404)
            return
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


@contextmanager
def _server(port: int = 0):
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_client_recovers_after_real_http_restart():
    """The same backend survives downtime and reconnects to the replacement server."""
    with _server() as port:
        backend = SdrForgeRestRadioBackend(f"http://127.0.0.1:{port}", timeout=0.2)
        assert backend.health()
        assert backend.get_frequency() == 94700000

    assert not backend.health()
    # Keep the same client and socket address; a new HTTP server owns the port.
    with _server(port):
        assert backend.health()
        assert backend.get_frequency() == 94700000


def test_read_waits_for_delayed_replacement_server():
    with _server() as port:
        backend = SdrForgeRestRadioBackend(f"http://127.0.0.1:{port}", timeout=0.2)
        assert backend.get_frequency() == 94700000

    started = threading.Event()
    release = threading.Event()
    errors: list[BaseException] = []
    values: list[int] = []

    def read_during_restart():
        started.set()
        try:
            values.append(backend.get_frequency())
        except BaseException as exc:
            errors.append(exc)
        finally:
            release.set()

    worker = threading.Thread(target=read_during_restart, daemon=True)
    worker.start()
    assert started.wait(timeout=1)
    # Let the read observe the refused connection before the server returns.
    time.sleep(0.15)
    with _server(port):
        assert release.wait(timeout=5), "read did not recover before deadline"
    worker.join(timeout=1)
    assert not errors, errors
    assert values == [94700000]
