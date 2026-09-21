# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Renderer-independent geocoding value objects."""

from __future__ import annotations

from dataclasses import dataclass

from ui.navigation import GeoPoint


@dataclass(frozen=True, slots=True)
class GeocodeResult:
    """One candidate returned by a geocoder."""

    display_name: str
    position: GeoPoint
    confidence: float
    source: str
