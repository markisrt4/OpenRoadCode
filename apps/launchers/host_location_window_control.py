# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Loopback-only window dismissal; no location data or permission changes."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class HostLocationWindowControl:
    def __init__(self, *, origins, hide, port=8767):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                origin = self.headers.get('Origin')
                if self.path != '/hide' or origin not in origins:
                    self.send_error(403)
                    return
                try:
                    hidden = hide()
                except (OSError, RuntimeError):
                    hidden = False
                self.send_response(204 if hidden else 409)
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Content-Length', '0')
                self.end_headers()

            def log_message(self, *_args):
                pass

        self._server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_port
        self._thread = Thread(target=lambda: self._server.serve_forever(poll_interval=.1), daemon=True)
        self._thread.start()

    def close(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=1)
