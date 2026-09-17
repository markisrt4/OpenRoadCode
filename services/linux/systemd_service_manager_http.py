# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""HTTP control plane for OpenRoadCode services supervised by systemd."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess

from services.common.service_manager_auth import TOKEN_ENV, authorized as _authorized, binding_allowed as _binding_allowed
from services.common.service_manager_client_store import ServiceManagerClientStore
from services.common.service_manager_pairing import ServiceManagerPairing
from services.linux.systemd_service_manager import ServiceStatus, SystemdServiceManager

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8769
CLIENT_STORE_ENV = "OPENROADCODE_SERVICE_MANAGER_CLIENT_STORE"
DEFAULT_CLIENT_STORE = "/var/lib/openroadcode/service-manager/authorized-clients.json"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _payload(statuses: tuple[ServiceStatus, ...] | list[ServiceStatus]) -> dict[str, object]:
    return {"services": [asdict(status) for status in statuses]}


class SystemdServiceManagerHandler(BaseHTTPRequestHandler):
    """Serve the same restricted service-management API used by Termux."""

    manager = SystemdServiceManager()
    auth_token: str | None = None
    pairing = ServiceManagerPairing()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if not self._authenticate():
            return
        if self.path.rstrip("/") != "/services":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        self._json(HTTPStatus.OK, _payload(self.manager.all_status()))

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parts = [part for part in self.path.split("/") if part]
        if parts == ["pair"]:
            self._pair()
            return
        if parts == ["pairing", "start"]:
            if not self._authenticate_admin():
                return
            pin, expires_at = self.pairing.begin()
            self._json(HTTPStatus.OK, {"pin": pin, "expires_at": expires_at})
            return
        if not self._authenticate():
            return
        try:
            if parts == ["stack", "core", "start"]:
                statuses = self.manager.start_core()
            elif parts == ["stack", "core", "stop"]:
                statuses = self.manager.stop_core()
            elif (
                len(parts) == 4
                and parts[0] == "services"
                and parts[2] == "profile"
            ):
                statuses = (self.manager.set_profile(parts[1], parts[3]),)
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

    def _pair(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            client_id, token = self.pairing.pair(
                str(payload.get("pin", "")),
                str(payload.get("client_name", "")),
            )
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._json(HTTPStatus.OK, {"client_id": client_id, "access_token": token})

    def _authenticate_admin(self) -> bool:
        if _authorized(self.headers.get("Authorization"), self.auth_token):
            return True
        self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return False

    def _authenticate(self) -> bool:
        header = self.headers.get("Authorization")
        if _authorized(header, self.auth_token):
            return True
        if header and header.startswith("Bearer ") and self.pairing.authorized(header.removeprefix("Bearer ")):
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

    client_store_path = Path(os.environ.get(CLIENT_STORE_ENV, DEFAULT_CLIENT_STORE))
    SystemdServiceManagerHandler.auth_token = token
    SystemdServiceManagerHandler.pairing = ServiceManagerPairing(
        store=ServiceManagerClientStore(client_store_path)
    )
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
