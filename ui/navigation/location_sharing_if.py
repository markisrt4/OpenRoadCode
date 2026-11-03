# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Immutable SI location and an optional Android location-provider contract."""
from dataclasses import dataclass
from typing import Protocol
from ui.navigation import GeoPoint


@dataclass(frozen=True)
class LocationSnapshot:
    point: GeoPoint | None = None
    sampled_at_s: float | None = None
    accuracy_m: float | None = None
    source: str = 'unknown'
    is_cached: bool = False


class AndroidLocationProviderIf(Protocol):
    def send_location(self, point: GeoPoint, accuracy_m: float) -> None:
        """Deliver a fresh location to the explicitly configured Android device."""
        ...

    def clear_location(self) -> None:
        """Remove only the provider created by this instance."""
        ...
