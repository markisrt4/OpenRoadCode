# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Explicitly authenticated Android SMS credential provisioning.

The Service Manager must route only /sms/provision here, before its ordinary
localhost-authentication bypass. A paired runtime token alone is insufficient.
"""

from __future__ import annotations

from http import HTTPStatus
import hmac
import json
import os

from services.common.service_manager_sms_credentials import delete_token, load_token, save_token

PROVISION_PATH = "/sms/provision"
PROVISION_TOKEN_ENV = "OPENROADCODE_SMS_PROVISION_TOKEN"
MAX_BODY_BYTES = 512


def serve_sms_provision(handler: object, method: str) -> bool:
    """Handle privileged provisioning; never return the stored credential."""
    from urllib.parse import urlsplit

    if urlsplit(handler.path).path != PROVISION_PATH:
        return False
    if method not in ("POST", "DELETE", "GET"):
        handler._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"})
        return True

    expected = os.environ.get(PROVISION_TOKEN_ENV, "")
    supplied = handler.headers.get("Authorization", "")
    if (
        len(expected) < 32
        or not supplied.startswith("Bearer ")
        or not hmac.compare_digest(supplied[7:], expected)
    ):
        handler._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return True

    if method == "GET":
        handler._json(HTTPStatus.OK, {"provisioned": load_token() is not None})
        return True
    if method == "DELETE":
        try:
            delete_token()
        except OSError:
            handler._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "provisioning failed"})
            return True
        handler._json(HTTPStatus.OK, {"provisioned": False})
        return True

    try:
        length = int(handler.headers.get("Content-Length", "-1"))
        if not 0 < length <= MAX_BODY_BYTES:
            raise ValueError("invalid length")
        body = handler.rfile.read(length)
        if len(body) != length:
            raise ValueError("incomplete body")
        payload = json.loads(body)
        if not isinstance(payload, dict) or set(payload) != {"token"}:
            raise ValueError("invalid payload")
        save_token(payload["token"])
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        handler._json(HTTPStatus.BAD_REQUEST, {"error": "invalid provisioning request"})
        return True
    except OSError:
        handler._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "provisioning failed"})
        return True
    handler._json(HTTPStatus.OK, {"provisioned": True})
    return True
