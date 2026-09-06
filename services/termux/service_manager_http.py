# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Local HTTP control plane for OpenRoadCode services supervised by runit."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import subprocess

from services.termux.service_manager import RunitServiceManager, ServiceStatus

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8768


def _payload(statuses: tuple[ServiceStatus, ...] | list[ServiceStatus]) -> dict[str, object]:
    return {"services": [asdict(status) for status in statuses]}


class ServiceManagerHandler(BaseHTTPRequestHandler):
    """Serve a deliberately small localhost-only service-management API."""

    manager = RunitServiceManager()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path.rstrip("/") != "/services":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        self._json(HTTPStatus.OK, _payload(self.manager.all_status()))

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parts = [part for part in self.path.split("/") if part]
        try:
            if parts == ["stack", "core", "start"]:
                statuses = self.manager.start_core()
            elif parts == ["stack", "core", "stop"]:
                statuses = self.manager.stop_core()
            elif len(parts) == 3 and parts[0] == "services" and parts[2] in {"start", "stop", "restart"}:
                action = getattr(self.manager, parts[2])
                statuses = (action(parts[1]),)
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
        except (ValueError, subprocess.SubprocessError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._json(HTTPStatus.OK, _payload(statuses))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Control OpenRoadCode Termux runit services.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("service manager must remain bound to localhost")
    server = ThreadingHTTPServer((args.host, args.port), ServiceManagerHandler)
    print(f"OpenRoadCode Termux service manager listening on {args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
