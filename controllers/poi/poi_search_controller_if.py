# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public interface for UI-independent POI discovery and selection."""

from abc import ABC, abstractmethod

from controllers.poi.poi_models import PoiCategory, PoiSearchResult, PointOfInterest, TransitMode


class PoiSearchControllerIf(ABC):
    """Coordinate POI search and selection independently of any frontend."""

    @abstractmethod
    def search(self, category: PoiCategory, transit_mode: TransitMode = TransitMode.ALL) -> None:
        """Request discovery of nearby places, optionally filtering public transit.

        @param category POI category to discover.
        @param transit_mode Transit subtype filter for transit searches.
        """
        ...

    @abstractmethod
    def poll_selected(self) -> PointOfInterest | None:
        """Return the latest selected POI, if one is available.

        @return Latest selected POI, or None when no selection is pending.
        """
        ...

    @abstractmethod
    def poll_search_result(self) -> PoiSearchResult | None:
        """Return the latest completed POI search result, if available.

        @return Latest completed search result, or None when none is pending.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear active POI search presentation."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Release resources owned by the controller."""
        ...
