# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Local HTTP control plane for OpenRoadCode services supervised by runit."""

from __future__ import annotations

import argparse
import html
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import subprocess

from common.xdg_paths import xdg_config_home
from services.common.service_manager_auth import TOKEN_ENV, authorized, binding_allowed, same_device_request
from services.common.service_manager_client_store import ServiceManagerClientStore
from services.common.service_manager_browser_pairing import (BrowserPairingConsumedError, ServiceManagerBrowserPairing)
from services.common.service_manager_pairing import ServiceManagerPairing
from services.termux.service_manager import RunitServiceManager, ServiceStatus

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8769
DEFAULT_CLIENT_STORE_PATH = xdg_config_home() / "openroadcode" / "service-manager" / "clients.json"


def _payload(statuses: tuple[ServiceStatus, ...] | list[ServiceStatus]) -> dict[str, object]:
    return {"services": [asdict(status) for status in statuses]}


class ServiceManagerHandler(BaseHTTPRequestHandler):
    """Serve a deliberately small service-management API."""

    manager = RunitServiceManager()
    auth_token: str | None = None
    pairing = ServiceManagerPairing()
    browser_pairing = ServiceManagerBrowserPairing(pairing)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parts = [part for part in self.path.split("/") if part]
        if len(parts) == 4 and parts[:3] == ["pairing", "browser", "approve"]:
            self._browser_approval_page(parts[3])
            return
        if len(parts) == 4 and parts[:3] == ["pairing", "browser", "status"]:
            self._browser_pairing_status(parts[3])
            return
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
        if parts == ["pairing", "browser", "start"]:
            self._browser_pairing_start()
            return
        if len(parts) == 4 and parts[:3] == ["pairing", "browser", "approve"]:
            self._browser_pairing_approve(parts[3])
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
            elif len(parts) == 4 and parts[0] == "services" and parts[2] == "profile":
                statuses = (self.manager.set_profile(parts[1], parts[3]),)
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

    def _browser_pairing_start(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            session, poll_token, approval_pin = self.browser_pairing.begin(str(payload.get("client_name", "")))
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        print(f"OpenRoadCode browser pairing PIN for {session.client_name}: {approval_pin}", flush=True)
        host = self.headers.get("Host", f"127.0.0.1:{self.server.server_port}")
        approval_url = f"http://{host}/pairing/browser/approve/{session.session_id}"
        self._json(HTTPStatus.OK, {
            "session_id": session.session_id,
            "poll_token": poll_token,
            "approval_url": approval_url,
            "expires_at": session.expires_at,
        })

    def _browser_pairing_status(self, session_id: str) -> None:
        session = self.browser_pairing.get(session_id)
        if session is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "pairing session not found or expired"})
            return
        poll_token = self.headers.get("X-OpenRoadCode-Pairing-Token", "")
        try:
            credentials = self.browser_pairing.complete(session_id, poll_token)
        except PermissionError:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        except BrowserPairingConsumedError:
            self._json(HTTPStatus.GONE, {"error": "pairing session already consumed"})
            return
        if credentials is None:
            self._json(HTTPStatus.OK, {"status": "pending"})
            return
        client_id, token = credentials
        self._json(HTTPStatus.OK, {
            "status": "approved", "client_id": client_id, "access_token": token
        })

    def _browser_approval_page(self, session_id: str) -> None:
        session = self.browser_pairing.get(session_id)
        if session is None:
            self._html(HTTPStatus.NOT_FOUND, "<h1>Pairing session expired</h1>")
            return
        client_name = html.escape(session.client_name)
        local = self._same_device_request()
        authentication = (
            "<p>This approval is being made on the OpenRoadCode device.</p>"
            if local else
            "<p>Enter the short-lived pairing PIN shown on the OpenRoadCode host.</p>"
            "<label>Pairing PIN<br><input type='text' name='approval_pin' "
            "inputmode='numeric' pattern='[0-9]{6}' maxlength='6' autocomplete='one-time-code' required></label><br><br>"
        )
        body = (
            "<h1>OpenRoadCode pairing</h1>"
            f"<p><strong>{client_name}</strong> wants permission to control this runtime.</p>"
            f"{authentication}"
            f"<form method='post' action='/pairing/browser/approve/{session.session_id}'>"
            "<button type='submit'>Approve device</button></form>"
        )
        self._html(HTTPStatus.OK, body)

    def _browser_pairing_approve(self, session_id: str) -> None:
        session = self.browser_pairing.get(session_id)
        if session is None:
            self._html(HTTPStatus.NOT_FOUND, "<h1>Pairing session expired</h1>")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            from urllib.parse import parse_qs
            approval_pin = parse_qs(raw).get("approval_pin", [""])[0]
        except (ValueError, UnicodeDecodeError):
            approval_pin = ""
        try:
            approved = self.browser_pairing.approve(
                session_id, None if self._same_device_request() else approval_pin
            )
        except PermissionError:
            self._html(
                HTTPStatus.UNAUTHORIZED,
                "<h1>OpenRoadCode pairing</h1><p>Pairing PIN was not accepted.</p>"
                f"<p><a href='/pairing/browser/approve/{session_id}'>Try again</a></p>",
            )
            return
        if not approved:
            self._html(HTTPStatus.NOT_FOUND, "<h1>Pairing session expired</h1>")
            return
        self._html(
            HTTPStatus.OK,
            "<h1>Device approved</h1>"
            "<p>OpenRoadCode Android Bridge has been authorized.</p>"
            "<p>You may return to the app.</p>",
        )

    def _same_device_request(self) -> bool:
        return same_device_request(self.client_address[0], self.connection.getsockname()[0])

    def _html(self, status: HTTPStatus, body: str) -> None:
        encoded = ("<!doctype html><meta name='viewport' content='width=device-width'>"
                   "<title>OpenRoadCode pairing</title>" + body).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

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
        if authorized(self.headers.get("Authorization"), self.auth_token):
            return True
        self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return False

    def _authenticate(self) -> bool:
        # Ordinary control requests originating on this device do not need the
        # bootstrap/admin credential. Keep privileged pairing administration
        # behind _authenticate_admin().
        if self.client_address[0] in {"127.0.0.1", "::1"}:
            return True
        header = self.headers.get("Authorization")
        if authorized(header, self.auth_token):
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
    parser = argparse.ArgumentParser(description="Control OpenRoadCode Termux runit services.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    token = os.environ.get(TOKEN_ENV, "").strip() or None
    if not binding_allowed(args.host, token):
        parser.error(f"non-loopback service manager requires {TOKEN_ENV}")
    ServiceManagerHandler.auth_token = token
    ServiceManagerHandler.pairing = ServiceManagerPairing(
        client_store=ServiceManagerClientStore(DEFAULT_CLIENT_STORE_PATH)
    )

    ServiceManagerHandler.browser_pairing = ServiceManagerBrowserPairing(ServiceManagerHandler.pairing)
    server = ThreadingHTTPServer((args.host, args.port), ServiceManagerHandler)
    auth_mode = "bearer token" if token else "localhost only"
    print(f"OpenRoadCode Termux service manager listening on {args.host}:{args.port} ({auth_mode})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
