# SPDX-License-Identifier: MIT
"""Bounded SDRForge readiness probe shared by REST clients.

A supervised PID is not proof that the HTTP API is accepting requests.
Only safe GET health probes are retried; mutations are never replayed.
"""

from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


class SdrforgeNotReadyError(RuntimeError):
    """The SDRForge health endpoint did not become ready in time."""


def wait_for_sdrforge_ready(
    base_url: str = "http://127.0.0.1:5570",
    *,
    timeout: float = 10.0,
    interval: float = 0.2,
    request_timeout: float = 0.5,
) -> None:
    """Wait for a valid healthy response, with a monotonic deadline."""
    if timeout < 0 or interval <= 0 or request_timeout <= 0:
        raise ValueError("invalid SDRForge readiness timing")
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while True:
        remaining = deadline - time.monotonic()
        try:
            with urlopen(
                base_url.rstrip("/") + "/v1/health",
                timeout=min(request_timeout, max(0.001, remaining)),
            ) as response:
                payload = json.load(response)
            if isinstance(payload, dict) and payload.get("status") == "ok":
                return
            last_error = ValueError("SDRForge health status is not ok")
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SdrforgeNotReadyError(
                f"SDRForge not ready after {timeout:g}s: {last_error}"
            ) from last_error
        time.sleep(min(interval, remaining))
