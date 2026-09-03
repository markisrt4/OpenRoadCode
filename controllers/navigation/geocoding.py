# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Domain models and contracts for resolving street addresses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GeocodedLocation:
    """A geographic location resolved from a human-readable address."""

    formatted_address: str
    latitude_deg: float
    longitude_deg: float

    def __post_init__(self) -> None:
        if not self.formatted_address.strip():
            raise ValueError("formatted_address must not be empty")
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("latitude_deg must be between -90 and 90")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("longitude_deg must be between -180 and 180")


class GeocoderIf(Protocol):
    """Resolve a human-readable address to a geographic location."""

    def geocode(self, address: str) -> GeocodedLocation | None:
        """Resolve address, returning None when no suitable match exists."""
        ...
