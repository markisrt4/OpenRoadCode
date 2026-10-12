# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Installer-owned loopback map server and browser lifecycle."""

import json
import secrets
import shutil
import subprocess
import threading
import math
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from frontends.common.destination_map_confirmation import HTML, validate_position


def confirm_on_map(destination, *, timeout=600, open_url=None):
    """Open a map, await a user-confirmed pin, and close the temporary server."""
    token = secrets.token_urlsafe(24)
    done, result = threading.Event(), []
    data = dict(label=destination.label, address=destination.address, token=token,
                lat=math.degrees(destination.position.latitude_rad),
                lon=math.degrees(destination.position.longitude_rad))
    page = HTML.replace("__DATA__", json.dumps(data).replace("<", "\\u003c")).encode()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def authorized(self):
            return parse_qs(urlsplit(self.path).query).get("token") == [token]

        def do_GET(self):
            if not self.authorized():
                self.send_error(403)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self):
            if urlsplit(self.path).path != "/confirm" or not self.authorized():
                self.send_error(403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("Invalid request")
                payload = json.loads(self.rfile.read(length))
                position = None if payload.get("cancel") is True else validate_position(payload)
            except (ValueError, KeyError, TypeError):
                self.send_error(400)
                return
            if not done.is_set():
                result.append(None if position is None else replace(destination, position=position))
            body = b'{"confirmed":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            # The waiting terminal may shut down the server after this event.
            # Finish sending the browser acknowledgment first.
            done.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/?token={token}"
    try:
        if open_url is not None:
            open_url(url)
        else:
            executable = shutil.which("termux-open-url") or shutil.which("xdg-open")
            if executable is None:
                raise RuntimeError("No browser opener available for map confirmation")
            subprocess.Popen([executable, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not done.wait(timeout):
            raise RuntimeError("Map confirmation timed out; destination was not saved")
        return result[0]
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
