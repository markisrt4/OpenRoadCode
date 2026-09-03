# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Cached orchestration for address geocoding."""

from __future__ import annotations

from controllers.navigation.geocode_cache import GeocodeCache
from controllers.navigation.geocoding import GeocodedLocation, GeocoderIf


class GeocodingController:
    """Resolve addresses while transparently reusing persistent results."""

    def __init__(self, geocoder: GeocoderIf, cache: GeocodeCache) -> None:
        self._geocoder = geocoder
        self._cache = cache

    def geocode(self, address: str) -> GeocodedLocation | None:
        """Resolve address from cache first, then the configured geocoder."""
        if not address.strip():
            raise ValueError("address must not be empty")

        cached = self._cache.load(address)
        if cached is not None:
            return cached

        location = self._geocoder.geocode(address)
        if location is not None:
            self._cache.store(address, location)
        return location
