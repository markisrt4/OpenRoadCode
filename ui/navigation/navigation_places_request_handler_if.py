# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation places operations without storage, renderer, or platform coupling."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.poi_models import PoiAction, PoiCategory, PoiSearchResult, PointOfInterest, TransitMode


@dataclass(frozen=True, slots=True)
class MapFavorite:
    """Named geographic destination in normalized SI coordinates."""

    favorite_id: str
    name: str
    position: GeoPoint


class NavigationPlacesRequestHandlerIf(ABC):
    """Handle places operations for one mounted navigation view."""

    @abstractmethod
    def favorite(self, key: str) -> MapFavorite | None:
        """Return a saved shortcut destination.

        @param key Shortcut name, home or work.
        @return Saved location, or None when unconfigured.
        """
        ...

    @abstractmethod
    def search(self, category: PoiCategory, transit_mode: TransitMode = TransitMode.ALL) -> None:
        """Request nearby places for the current viewport.

        @param category Semantic place category.
        @param transit_mode Optional public transport filter.
        """
        ...

    @abstractmethod
    def poll_search_result(self) -> PoiSearchResult | None:
        """Consume a completed search.

        @return Immutable search result, or None when none is pending.
        """
        ...

    @abstractmethod
    def poll_selected(self) -> PointOfInterest | None:
        """Consume a selected place.

        @return Selected place, or None when none is pending.
        """
        ...

    @abstractmethod
    def poll_camera_interaction(self) -> bool:
        """Consume a native map interaction notification.

        @return True when a manual camera interaction occurred.
        """
        ...

    @abstractmethod
    def execute(self, poi: PointOfInterest, action: PoiAction) -> str:
        """Perform a semantic place action using the backend platform adapter.

        @param poi Selected place.
        @param action Requested action.
        @return User-facing action status.
        @throws ValueError When the action is invalid or unavailable.
        @throws RuntimeError When the platform action fails.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Invalidate pending searches and selections."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Idempotently release this view's search session."""
        ...


class NavigationPlacesFactoryIf(ABC):
    """Provide a backend session when a navigation view is mounted."""

    @abstractmethod
    def create(self) -> NavigationPlacesRequestHandlerIf:
        """Create a fresh contract-bound session.

        @return Places handler owned by the mounted view lifecycle.
        """
        ...
