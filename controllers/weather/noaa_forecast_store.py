# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Thread-safe, transport-independent NOAA RF forecast snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import time
from typing import Callable, Mapping


@dataclass(frozen=True, slots=True)
class NoaaForecastSnapshot:
    """Immutable received forecast with explicit geographic uncertainty."""

    area: str | None
    areas: tuple[str, ...]
    period: str
    conditions: str | None
    high_f: float | None
    low_f: float | None
    precipitation_chance_percent: float | None
    frequency_hz: int | None
    cycle: int
    revision: int
    received_at: float
    boundary_suspected: bool

    @property
    def geographically_scoped(self) -> bool:
        """Whether the publisher identified a specific forecast area."""
        return bool(self.area)


class NoaaForecastStore:
    """Hold the latest received NOAA forecast without guessing its location."""

    def __init__(self, *, clock: Callable[[], float] = time) -> None:
        self._clock = clock
        self._lock = RLock()
        self._latest: NoaaForecastSnapshot | None = None

    def ingest(self, event: Mapping[str, object]) -> NoaaForecastSnapshot:
        """Validate and atomically store a completed NOAA forecast event."""
        if event.get("event") != "noaa_forecast_completed":
            raise ValueError("expected noaa_forecast_completed")
        completed = event.get("completed_forecast")
        if not isinstance(completed, dict):
            raise ValueError("completed_forecast must be an object")
        forecast = completed.get("forecast")
        if not isinstance(forecast, dict):
            raise ValueError("forecast must be an object")
        period = forecast.get("period")
        if not isinstance(period, str) or not period.strip():
            raise ValueError("forecast period is required")
        area = event.get("forecast_area")
        if area is not None and not isinstance(area, str):
            raise ValueError("forecast_area must be a string or null")
        areas = event.get("forecast_areas", [])
        if not isinstance(areas, list) or not all(isinstance(a, str) for a in areas):
            raise ValueError("forecast_areas must be a list of strings")
        conditions = forecast.get("conditions")
        if conditions is not None and not isinstance(conditions, str):
            raise ValueError("conditions must be a string or null")

        def optional_number(key: str) -> float | None:
            value = forecast.get(key)
            if value is None:
                return None
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{key} must be numeric or null")
            from math import isfinite
            if not isfinite(value):
                raise ValueError(f"{key} must be finite")
            return float(value)

        def integer(key: str, default: int = 0) -> int:
            value = event.get(key, default)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{key} must be a nonnegative integer")
            return value

        frequency = event.get("source_frequency_hz")
        if frequency is not None and (
            isinstance(frequency, bool) or not isinstance(frequency, int) or frequency <= 0
        ):
            raise ValueError("source_frequency_hz must be a positive integer or null")
        boundary = event.get("cycle_boundary_suspected", False)
        if not isinstance(boundary, bool):
            raise ValueError("cycle_boundary_suspected must be boolean")
        chance = optional_number("precipitation_chance_percent")
        if chance is not None and not 0 <= chance <= 100:
            raise ValueError("precipitation chance must be between 0 and 100")
        snapshot = NoaaForecastSnapshot(
            area=area.strip() or None if area is not None else None,
            areas=tuple(areas),
            period=period.strip(),
            conditions=conditions,
            high_f=optional_number("high_f"),
            low_f=optional_number("low_f"),
            precipitation_chance_percent=chance,
            frequency_hz=frequency,
            cycle=integer("forecast_cycle"),
            revision=integer("forecast_revision"),
            received_at=self._clock(),
            boundary_suspected=boundary,
        )
        with self._lock:
            self._latest = snapshot
        return snapshot

    def latest(self) -> NoaaForecastSnapshot | None:
        """Return an immutable snapshot suitable for concurrent UI reads."""
        with self._lock:
            return self._latest

    def age_seconds(self) -> float | None:
        """Return age since reception, not forecast validity age."""
        with self._lock:
            snapshot = self._latest
        return None if snapshot is None else max(0.0, self._clock() - snapshot.received_at)
