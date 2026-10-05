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


@dataclass(frozen=True, slots=True)
class NavigationCameraState:
    """Observed camera with position and angles in radians."""

    center: GeoPoint
    zoom: float
    bearing_rad: float
    pitch_rad: float


@dataclass(frozen=True, slots=True)
class PlaceActionResult:
    """Completed semantic handoff, identified independently of a widget."""

    request_id: int
    status: str
    success: bool


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

    def poll_camera_state(self) -> NavigationCameraState | None:
        """Consume observed SI camera state.

        @return Latest camera or None."""
        return None

    def request_action(self, poi: PointOfInterest, action: PoiAction) -> int | None:
        """Start a handoff.

        @param poi Place.

        @param action Action.

        @return Request ID or None when busy."""
        return None

    def poll_action_result(self) -> PlaceActionResult | None:
        """Consume a completed handoff.

        @return Completion or None."""
        return None

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
