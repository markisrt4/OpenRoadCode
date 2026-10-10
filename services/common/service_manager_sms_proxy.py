# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Restricted, opt-in SMS gateway forwarding for the Termux service manager."""

from __future__ import annotations

from http import HTTPStatus
from http.client import HTTPConnection
import json
import os
from urllib.parse import urlsplit

from services.common.service_manager_messaging_auth import messaging_authorized
from services.common.service_manager_sms_credentials import load_token

ENABLED_ENV = "OPENROADCODE_SMS_ENABLED"
TOKEN_ENV = "OPENROADCODE_SMS_TOKEN"
ANDROID_TOKEN_ENV = "OPENROADCODE_ANDROID_SMS_TOKEN"
MAX_REQUEST_BYTES = 16 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
ALLOWED_ROUTES = {
    ("GET", "/sms/capabilities"),
    ("GET", "/sms/conversations"),
    ("GET", "/sms/messages"),
    ("POST", "/sms/send"),
}


def serve_sms(handler: object, method: str) -> bool:
    """Handle only declared SMS routes; return False for unrelated requests."""
    path = urlsplit(handler.path).path
    if (method, path) not in ALLOWED_ROUTES:
        return False

    enabled = os.environ.get(ENABLED_ENV) == "1"
    external_token = os.environ.get(TOKEN_ENV, "").strip() or None
    internal_token = os.environ.get(ANDROID_TOKEN_ENV, "").strip() or load_token()
    if not enabled or not external_token or not internal_token:
        handler._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "SMS gateway disabled"})
        return True
    if not messaging_authorized(
        handler.headers.get("Authorization"), enabled=True, messaging_token=external_token
    ):
        handler._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return True

    body = b""
    if method == "POST":
        try:
            length = int(handler.headers.get("Content-Length", "-1"))
            if length < 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("invalid body length")
            body = handler.rfile.read(length)
            if len(body) != length or not isinstance(json.loads(body), dict):
                raise ValueError("invalid JSON object")
        except (ValueError, UnicodeDecodeError):
            handler._json(HTTPStatus.BAD_REQUEST, {"error": "invalid SMS request"})
            return True

    # Never accept a client-supplied upstream URL. Android gateway is loopback only.
    target = path
    if method == "GET" and urlsplit(handler.path).query:
        target += "?" + urlsplit(handler.path).query
    connection = HTTPConnection("127.0.0.1", 8773, timeout=3)
    try:
        connection.request(
            method, target, body=body if method == "POST" else None,
            headers={
                "Authorization": "Bearer " + internal_token,
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        if response.status not in (200, 201, 202, 400, 401, 403, 404, 409, 422):
            handler._json(HTTPStatus.BAD_GATEWAY, {"error": "SMS gateway unavailable"})
            return True
        size = response.getheader("Content-Length")
        if size is not None and (not size.isdecimal() or int(size) > MAX_RESPONSE_BYTES):
            raise ValueError("oversized response")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("oversized response")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("invalid response")
        handler._json(HTTPStatus(response.status), payload)
    except (OSError, ValueError, json.JSONDecodeError):
        handler._json(HTTPStatus.BAD_GATEWAY, {"error": "SMS gateway unavailable"})
    finally:
        connection.close()
    return True
