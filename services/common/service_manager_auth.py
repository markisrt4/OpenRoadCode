# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared authentication policy for OpenRoadCode service-manager HTTP endpoints."""

from __future__ import annotations

import hmac
import ipaddress

TOKEN_ENV = "OPENROADCODE_SERVICE_MANAGER_TOKEN"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def authorized(header_value: str | None, token: str | None) -> bool:
    """Return whether a request satisfies the configured bearer-token policy."""
    if not token:
        return True
    if not header_value or not header_value.startswith("Bearer "):
        return False
    supplied = header_value.removeprefix("Bearer ")
    return hmac.compare_digest(supplied, token)


def binding_allowed(host: str, token: str | None) -> bool:
    """Require authentication whenever the manager is reachable off-host."""
    return host in LOOPBACK_HOSTS or bool(token)


def same_device_request(client_host: str, server_host: str) -> bool:
    """Return whether both ends of the HTTP connection are on this device."""
    try:
        client = ipaddress.ip_address(client_host)
        server = ipaddress.ip_address(server_host)
    except ValueError:
        return False
    return client.is_loopback or client == server
