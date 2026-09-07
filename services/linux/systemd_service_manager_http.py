# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""HTTP control plane for OpenRoadCode services supervised by systemd."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import subprocess

from services.linux.systemd_service_manager import ServiceStatus, SystemdServiceManager

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8769
TOKEN_ENV = "OPENROADCODE_SERVICE_MANAGER_TOKEN"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _payload(statuses: tuple[ServiceStatus, ...] | list[ServiceStatus]) -> dict[str, object]:
    return {"services": [asdict(status) for status in statuses]}


def _authorized(header_value: str | None, token: str | None) -> bool:
    """Return whether the request satisfies the configured bearer-token policy."""
    if not token:
        return True
    if not header_value or not header_value.startswith("Bearer "):
        return False
    supplied = header_value.removeprefix("Bearer ")
    return hmac.compare_digest(supplied, token)


def _binding_allowed(host: str, token: str | None) -> bool:
    """Require authentication whenever the manager is reachable off-host."""
    return host in LOOPBACK_HOSTS or bool(token)


class SystemdServiceManagerHandler(BaseHTTPRequestHandler):
    """Serve the same restricted service-management API used by Termux."""

    manager = SystemdServiceManager()
    auth_token: str | None = None

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self._authenticate():
            return
        if self.path.rstrip("/") != "/services":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        self._json(HTTPStatus.OK, _payload(self.manager.all_status()))

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self._authenticate():
            return
        parts = [part for part in self.path.split("/") if part]
        try:
            if parts == ["stack", "core", "start"]:
                statuses = self.manager.start_core()
            elif parts == ["stack", "core", "stop"]:
                statuses = self.manager.stop_core()
            elif len(parts) == 3 and parts[0] == "services" and parts[2] in {
                "start",
                "stop",
                "restart",
            }:
                action = getattr(self.manager, parts[2])
                statuses = (action(parts[1]),)
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
        except (ValueError, subprocess.SubprocessError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._json(HTTPStatus.OK, _payload(statuses))

    def _authenticate(self) -> bool:
        if _authorized(self.headers.get("Authorization"), self.auth_token):
            return True
        self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return False

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Control OpenRoadCode Linux systemd services.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    token = os.environ.get(TOKEN_ENV, "").strip() or None
    if not _binding_allowed(args.host, token):
        parser.error(f"non-loopback service manager requires {TOKEN_ENV}")

    SystemdServiceManagerHandler.auth_token = token
    server = ThreadingHTTPServer((args.host, args.port), SystemdServiceManagerHandler)
    auth_mode = "bearer token" if token else "localhost only"
    print(
        f"OpenRoadCode systemd service manager listening on {args.host}:{args.port} "
        f"({auth_mode})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
