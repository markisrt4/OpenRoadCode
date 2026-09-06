# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Geocoding contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GeocodedLocation:
    formatted_address: str
    latitude_deg: float
    longitude_deg: float


class GeocoderIf(Protocol):
    def geocode(self, address: str) -> GeocodedLocation | None:
        """Resolve a human-readable address using an offline search source."""
        ...
