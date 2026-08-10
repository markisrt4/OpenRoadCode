from __future__ import annotations

from typing import Any

import requests


class ValhallaHttpClient:
    """Low-level HTTP client for a Valhalla service."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8002",
        *,
        timeout_seconds: float = 10.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def status(self) -> dict[str, Any]:
        response = requests.get(
            f"{self._base_url}/status",
            timeout=self._timeout_seconds,
        )

        response.raise_for_status()

        result = response.json()

        if not isinstance(result, dict):
            raise ValueError("Valhalla status response was not an object")

        return result

    def route(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        response = requests.post(
            f"{self._base_url}/route",
            json=request,
            timeout=self._timeout_seconds,
        )

        response.raise_for_status()

        result = response.json()

        if not isinstance(result, dict):
            raise ValueError("Valhalla route response was not an object")

        return result
