"""Low-level HTTP client for the Valhalla REST API."""

from __future__ import annotations

from typing import Any

import requests


class ValhallaHttpClient:
    """Send HTTP requests to a Valhalla routing service."""

    DEFAULT_BASE_URL = "http://127.0.0.1:8002"
    DEFAULT_TIMEOUT_SECONDS = 10.0

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not base_url:
            raise ValueError("base_url cannot be empty")

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero"
            )

        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def base_url(self) -> str:
        return self._base_url

    def status(self) -> dict[str, Any]:
        """Return Valhalla service status."""

        response = requests.get(
            f"{self._base_url}/status",
            timeout=self._timeout_seconds,
        )

        response.raise_for_status()

        result = response.json()

        if not isinstance(result, dict):
            raise ValueError(
                "Valhalla status response was not a JSON object"
            )

        return result

    def route(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Submit a route request."""

        response = requests.post(
            f"{self._base_url}/route",
            json=request,
            timeout=self._timeout_seconds,
        )

        response.raise_for_status()

        result = response.json()

        if not isinstance(result, dict):
            raise ValueError(
                "Valhalla route response was not a JSON object"
            )

        return result

