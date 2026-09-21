# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent cache for resolved street addresses."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from controllers.cache import PersistentCacheIf
from controllers.navigation.geocoding import GeocodedLocation


class GeocodeCache:
    """Serialize geocoded locations through the generic persistent cache."""

    KEY_PREFIX = "geocode:v1:"

    def __init__(self, storage: PersistentCacheIf) -> None:
        self._storage = storage

    def load(self, address: str) -> GeocodedLocation | None:
        """Return a cached location for address, if present and valid."""
        key = self._key(address)
        data = self._storage.get(key)
        if data is None:
            return None
        try:
            value = json.loads(data.decode("utf-8"))
            return self._decode(value)
        except (KeyError, TypeError, ValueError, UnicodeDecodeError):
            self._storage.remove(key)
            return None

    def store(self, address: str, location: GeocodedLocation) -> None:
        """Cache a resolved location under the normalized input address."""
        value = {
            "formatted_address": location.formatted_address,
            "latitude_deg": location.latitude_deg,
            "longitude_deg": location.longitude_deg,
        }
        self._storage.put(
            self._key(address),
            json.dumps(value, separators=(",", ":")).encode("utf-8"),
        )

    @classmethod
    def _key(cls, address: str) -> str:
        normalized = normalize_address(address)
        if not normalized:
            raise ValueError("address must not be empty")
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"{cls.KEY_PREFIX}{digest}"

    @staticmethod
    def _decode(value: Any) -> GeocodedLocation:
        if not isinstance(value, dict):
            raise ValueError("invalid geocode cache entry")
        return GeocodedLocation(
            formatted_address=str(value["formatted_address"]),
            latitude_deg=float(value["latitude_deg"]),
            longitude_deg=float(value["longitude_deg"]),
        )


def normalize_address(address: str) -> str:
    """Normalize insignificant whitespace/case for stable cache lookup."""
    return " ".join(address.split()).casefold()
