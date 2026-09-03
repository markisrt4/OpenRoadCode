# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Interface for geographic POI data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from controllers.poi.poi_models import PoiCategory, PointOfInterest


@dataclass(frozen=True, slots=True)
class PoiSearchBounds:
    """Geographic rectangle to search for points of interest."""

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.south <= 90.0 or not -90.0 <= self.north <= 90.0:
            raise ValueError("POI search latitude bounds must be between -90 and 90 degrees")
        if not -180.0 <= self.west <= 180.0 or not -180.0 <= self.east <= 180.0:
            raise ValueError("POI search longitude bounds must be between -180 and 180 degrees")
        if self.south > self.north:
            raise ValueError("POI search south bound must not exceed north bound")


@dataclass(frozen=True, slots=True)
class PoiSearchQuery:
    """Describe one deterministic POI search independent of map rendering."""

    category: PoiCategory
    bounds: PoiSearchBounds
    limit: int = 50

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("POI search limit must be positive")


class PoiSearchSourceIf(ABC):
    """Search a geographic POI dataset without depending on a renderer."""

    @abstractmethod
    def search(self, query: PoiSearchQuery) -> tuple[PointOfInterest, ...]:
        """Return POIs matching ``query`` within its geographic bounds."""
        ...

    def close(self) -> None:
        """Release source resources, if any."""
