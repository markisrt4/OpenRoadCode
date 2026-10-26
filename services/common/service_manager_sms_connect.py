# SPDX-License-Identifier: MIT
"""Local-only, SMS-specific browser approval and verified credential exchange.

Ordinary runtime pairing is never consulted. The Android credential is accepted
only after approval AND a successful authenticated GET of the actual loopback
Android gateway. No contacts/messages/send routes are used during setup.
"""
from __future__ import annotations

import html
from http import HTTPStatus
from http.client import HTTPConnection, HTTPException
import json
import os
import re
import secrets
import threading
from urllib.parse import parse_qs, urlsplit

from services.common.service_manager_browser_pairing import ServiceManagerBrowserPairing
from services.common.service_manager_pairing import ServiceManagerPairing
from services.common.service_manager_sms_credentials import client_token_path, load_token, save_token


class SetupBusyError(Exception):
    pass


class SmsConnectionSessions:
    def __init__(self):
        self.sessions = ServiceManagerBrowserPairing(ServiceManagerPairing(), ttl_seconds=180)
        self.lock = threading.Lock()

    def begin(self):
        with self.lock:
            if self.sessions.active_count() >= 16:
                raise SetupBusyError()
            return self.sessions.begin("ORC Companion messaging")

    def status(self, session_id, poll_token):
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if not self.sessions.poll_authorized(session, poll_token):
            raise PermissionError()
        return session


def _android_accepts(token):
    connection = HTTPConnection("127.0.0.1", 8773, timeout=3)
    try:
        connection.request("GET", "/sms/capabilities", headers={"Authorization": "Bearer " + token})
        response = connection.getresponse()
        if response.status != 200:
            return False
        raw = response.read(1025)
        return len(raw) <= 1024 and json.loads(raw).get("read_sms_granted") is True
    except (OSError, HTTPException, ValueError, AttributeError):
        return False
    finally:
        connection.close()


def _body(handler, form=False):
    length = int(handler.headers.get("Content-Length", "-1"))
    if not 0 <= length <= 1024:
        raise ValueError()
    raw = handler.rfile.read(length)
    if len(raw) != length:
        raise ValueError()
    value = parse_qs(raw.decode()) if form else json.loads(raw or b"{}")
    if not isinstance(value, dict):
        raise ValueError()
    return value


def _page(handler, status, body):
    data = ("<!doctype html><meta name='viewport' content='width=device-width'>"
            "<title>Connect messaging</title>" + body).encode()
    handler.send_response(status)
    for key, value in {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store",
                       "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
                       "Content-Security-Policy": "default-src 'none'; form-action 'self'; frame-ancestors 'none'",
                       "Content-Length": str(len(data))}.items():
        handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(data)


def serve_sms_connect(handler, method):
    target = urlsplit(handler.path)
    parts = target.path.strip("/").split("/")
    if parts[:2] != ["sms", "connect"]:
        return False
    if handler.client_address[0] not in ("127.0.0.1", "::1"):
        handler._json(HTTPStatus.FORBIDDEN, {"error": "Local phone setup only"})
        return True
    # A stalled local form submission must not hold the session lock indefinitely.
    handler.connection.settimeout(3)
    owner = handler.sms_connections
    try:
        if parts == ["sms", "connect", "start"] and method == "POST":
            _body(handler)
            session, poll, approval = owner.begin()
            port = handler.server.server_port
            handler._json(HTTPStatus.OK, {
                "session_id": session.session_id, "poll_token": poll,
                "approval_url": f"http://127.0.0.1:{port}/sms/connect/approve/{session.session_id}?token={approval}",
            })
            return True
        if len(parts) != 4 or parts[2] not in ("approve", "status", "complete", "cancel"):
            handler._json(HTTPStatus.NOT_FOUND, {"error": "Unknown messaging setup action"})
            return True
        action, sid = parts[2:]
        with owner.lock:
            if action == "approve" and method in ("GET", "POST"):
                session = owner.sessions.get(sid)
                if session is None or session.consumed:
                    _page(handler, 410, "<h1>Setup expired or closed</h1><p>Return to ORC Companion and try Connect messaging again.</p>")
                    return True
                if method == "GET":
                    approval = parse_qs(target.query).get("token", [""])[0]
                    owner.sessions.authorize_approval(sid, approval)
                    _page(handler, 200,
                          "<h1>Connect phone messages?</h1>"
                          "<p>Allow OpenRoadCode in Termux on this phone to access Android messages and contacts when Android permissions allow. "
                          "This is separate from runtime pairing. No message will be sent by setup.</p>"
                          "<p>Approve only if you just tapped Connect messaging in ORC Companion. "
                          "Desktop access still requires its separate SMS credential and secure connection. Individual sends require confirmation in TechForge.</p>"
                          f"<form method='post' action='/sms/connect/approve/{sid}'>"
                          f"<input type='hidden' name='approval_token' value='{html.escape(approval, quote=True)}'>"
                          "<button name='decision' value='approve'>Connect messaging</button> "
                          "<button name='decision' value='deny'>Cancel</button></form>")
                else:
                    form = _body(handler, form=True)
                    approval = form.get("approval_token", [""])[0]
                    owner.sessions.authorize_approval(sid, approval)
                    if form.get("decision", [""])[0] == "approve":
                        owner.sessions.approve(sid, approval)
                        _page(handler, 200, "<h1>Messaging approved</h1><p>Return to ORC Companion to finish and verify the connection.</p>")
                    else:
                        session.consumed = True
                        _page(handler, 200, "<h1>Setup cancelled</h1><p>No connection was created.</p>")
                return True
            bearer = handler.headers.get("Authorization", "")
            poll = bearer[7:] if bearer.startswith("Bearer ") else ""
            session = owner.status(sid, poll)
            if session is None:
                handler._json(HTTPStatus.GONE, {"error": "Setup expired. Tap Connect messaging again."})
                return True
            if action == "cancel" and method == "POST":
                _body(handler)
                session.consumed = True
                handler._json(HTTPStatus.OK, {"status": "cancelled"})
                return True
            if action == "status" and method == "GET":
                handler._json(HTTPStatus.OK, {"status": "closed" if session.consumed else "approved" if session.approved else "pending"})
                return True
            if action == "complete" and method == "POST":
                payload = _body(handler)
                if session.consumed or not session.approved:
                    handler._json(HTTPStatus.CONFLICT, {"error": "Setup is not awaiting completion"})
                    return True
                token = payload.get("token")
                if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
                    raise ValueError()
                if not _android_accepts(token):
                    handler._json(HTTPStatus.BAD_GATEWAY, {"error": "Enable messages and grant SMS read permission, then try again."})
                    return True
                client = load_token(client_token_path()) or os.environ.get("OPENROADCODE_SMS_TOKEN", "").strip()
                if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", client):
                    client = secrets.token_urlsafe(32)
                save_token(token)
                save_token(client, client_token_path())
                session.consumed = True
                handler._json(HTTPStatus.OK, {"status": "connected"})
                return True
            handler._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "Unsupported setup request"})
    except SetupBusyError:
        handler._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "Too many setup attempts. Wait three minutes and retry."})
    except PermissionError:
        handler._json(HTTPStatus.UNAUTHORIZED, {"error": "Setup authorization expired or invalid"})
    except (ValueError, TypeError, UnicodeError):
        handler._json(HTTPStatus.BAD_REQUEST, {"error": "Invalid messaging setup request"})
    except OSError:
        handler._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Cannot save private messaging setup. Check Termux storage access."})
    return True
