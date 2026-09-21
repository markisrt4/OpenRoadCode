# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract for converting user-entered locations into coordinates."""

from __future__ import annotations

from typing import Protocol

from controllers.navigation.geocoding_models import GeocodeResult


class GeocoderIf(Protocol):
    """Resolve a human-readable location query into ranked candidates."""

    def geocode(self, query: str, *, limit: int = 5) -> tuple[GeocodeResult, ...]:
        """Return ranked candidates for the query.

        @param query Human-readable location query to resolve.
        @param limit Maximum number of ranked candidates to return.
        @return Ranked geocoding candidates.
        """
        ...

    def close(self) -> None:
        """Release owned resources."""
        ...
