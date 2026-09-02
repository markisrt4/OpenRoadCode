# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public interface for UI-independent POI discovery and selection."""

from abc import ABC, abstractmethod

from controllers.poi.poi_models import PoiCategory, PoiSearchResult, PointOfInterest


class PoiSearchControllerIf(ABC):
    """Coordinate POI search and selection independently of any frontend."""

    @abstractmethod
    def search(self, category: PoiCategory) -> None:
        """Request discovery of places in the current geographic viewport."""
        ...

    @abstractmethod
    def poll_selected(self) -> PointOfInterest | None:
        """Return the latest selected POI, if one is available."""
        ...

    @abstractmethod
    def poll_search_result(self) -> PoiSearchResult | None:
        """Return the latest completed POI search result, if available."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear active POI search presentation."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Release resources owned by the controller."""
        ...
