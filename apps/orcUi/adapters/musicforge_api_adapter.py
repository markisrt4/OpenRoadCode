"""HTTP adapter for the versioned MusicForge charts API."""

from __future__ import annotations

from collections.abc import Callable
from time import monotonic
from typing import Any, cast

import httpx

from ui.radio.airplay_details import AirplayDetails, AirplayRequest


class MusicForgeApiAdapter:
    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)

    def stations(self) -> list[dict[str, Any]]:
        response = self._client.get("/api/v1/stations")
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json()["stations"])

    def songs(
        self, *, station: str | None = None, period: str = "today", limit: int = 20
    ) -> dict[str, Any]:
        return self._chart("songs", station, period, limit)

    def artists(
        self, *, station: str | None = None, period: str = "today", limit: int = 20
    ) -> dict[str, Any]:
        return self._chart("artists", station, period, limit)

    def _chart(self, kind: str, station: str | None, period: str, limit: int) -> dict[str, Any]:
        params: dict[str, str | int] = {"period": period, "limit": limit}
        if station:
            params["station"] = station
        response = self._client.get(f"/api/v1/charts/{kind}", params=params)
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def airplay_details(
        self, request: AirplayRequest, *, current: Callable[[], bool]
    ) -> AirplayDetails:
        """Look up chart counts without treating a missing ranked entry as zero."""
        chart = self.songs if request.title else self.artists
        filters: list[tuple[str, str | None, str]]
        if request.view == "trend":
            filters = [(period, request.station, period) for period in ("today", "7d", "30d")]
        else:
            stations = sorted({item["station"] for item in self.stations() if item.get("station")})
            filters = [(station, station, request.period) for station in stations]

        counts: list[tuple[str, int | None]] = []
        incomplete = False
        deadline = monotonic() + 12
        for label, station, period in filters:
            if not current() or monotonic() >= deadline:
                incomplete = True
                break
            try:
                entries = chart(station=station, period=period, limit=40).get("results", [])
            except (httpx.HTTPError, ValueError, RuntimeError):
                incomplete = True
                continue
            count = next(
                (
                    item["plays"]
                    for item in entries
                    if item.get("artist") == request.artist
                    and (request.title is None or item.get("title") == request.title)
                    and isinstance(item.get("plays"), int)
                ),
                None,
            )
            counts.append((label, count))
        if request.view == "stations":
            counts.sort(key=lambda row: -(row[1] if row[1] is not None else -1))
        return AirplayDetails(tuple(counts), incomplete)

    def close(self) -> None:
        self._client.close()
