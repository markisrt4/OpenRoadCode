# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Low-level Termux:API geographic location access."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TermuxLocationData:
    """Represent one location report returned by Android."""

    latitude_deg: float | None = None
    longitude_deg: float | None = None
    altitude_m: float | None = None
    accuracy_m: float | None = None
    vertical_accuracy_m: float | None = None
    bearing_deg: float | None = None
    speed_mps: float | None = None
    elapsed_ms: int | None = None
    provider: str | None = None


class TermuxLocationClient:
    """Read Android location through the ``termux-location`` command."""

    @property
    def is_available(self) -> bool:
        return shutil.which("termux-location") is not None

    def read(self, *, provider: str = "gps", request: str = "once") -> TermuxLocationData:
        if not self.is_available:
            raise RuntimeError("termux-location is not available; install Termux:API and the termux-api package")

        result = subprocess.run(
            ["termux-location", "-p", provider, "-r", request],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected JSON payload from termux-location")

        def optional_float(name: str) -> float | None:
            value = payload.get(name)
            return float(value) if value is not None else None

        elapsed_ms = payload.get("elapsedMs")
        return TermuxLocationData(
            latitude_deg=optional_float("latitude"),
            longitude_deg=optional_float("longitude"),
            altitude_m=optional_float("altitude"),
            accuracy_m=optional_float("accuracy"),
            vertical_accuracy_m=optional_float("vertical_accuracy"),
            bearing_deg=optional_float("bearing"),
            speed_mps=optional_float("speed"),
            elapsed_ms=int(elapsed_ms) if elapsed_ms is not None else None,
            provider=str(payload["provider"]) if payload.get("provider") is not None else None,
        )
