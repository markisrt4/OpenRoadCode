"""HTTP adapter for the versioned MusicForge charts API."""
from __future__ import annotations

import httpx


class MusicForgeApiAdapter:
    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)

    def stations(self) -> list[dict]:
        response = self._client.get("/api/v1/stations")
        response.raise_for_status()
        return response.json()["stations"]

    def songs(self, *, station: str | None = None, period: str = "today",
              limit: int = 20) -> dict:
        return self._chart("songs", station, period, limit)

    def artists(self, *, station: str | None = None, period: str = "today",
                limit: int = 20) -> dict:
        return self._chart("artists", station, period, limit)

    def _chart(self, kind: str, station: str | None, period: str, limit: int) -> dict:
        params = {"period": period, "limit": limit}
        if station:
            params["station"] = station
        response = self._client.get(f"/api/v1/charts/{kind}", params=params)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()
