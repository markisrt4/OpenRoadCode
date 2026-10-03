# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt POI discovery, saved places, and platform actions to UI contracts."""
from controllers.navigation.map_favorites import MapFavorites
from controllers.poi.poi_search_controller_if import PoiSearchControllerIf
from controllers.poi.poi_action_executor_if import PoiActionExecutorIf
from ui.navigation.navigation_places_request_handler_if import MapFavorite, NavigationPlacesRequestHandlerIf
from ui.navigation.poi_models import PoiAction, PoiCategory, PoiSearchResult, PointOfInterest, TransitMode


class NavigationPlacesController(NavigationPlacesRequestHandlerIf):
    """Own one search session while sharing durable favorites and action adapters."""

    def __init__(self, search: PoiSearchControllerIf, favorites: MapFavorites, actions: PoiActionExecutorIf):
        self._search = search
        self._favorites = favorites
        self._actions = actions
        self._closed = False

    def favorite(self, key: str) -> MapFavorite | None:
        if self._closed:
            return None
        if key not in {'home', 'work'}:
            raise ValueError(f'Unknown destination shortcut: {key}')
        return self._favorites.home if key == 'home' else self._favorites.work

    def search(self, category: PoiCategory, transit_mode: TransitMode = TransitMode.ALL) -> None:
        if not self._closed:
            self._search.search(category, transit_mode)

    def poll_search_result(self) -> PoiSearchResult | None:
        return None if self._closed else self._search.poll_search_result()

    def poll_selected(self) -> PointOfInterest | None:
        return None if self._closed else self._search.poll_selected()

    def poll_camera_interaction(self) -> bool:
        return False if self._closed else self._search.poll_camera_interaction()

    def execute(self, poi: PointOfInterest, action: PoiAction) -> str:
        if self._closed:
            raise RuntimeError('Navigation places session is closed')
        try:
            return self._actions.execute(poi, action)
        except ValueError:
            raise
        except Exception as error:
            # Frontends handle contract errors without importing Android launcher types.
            raise RuntimeError(str(error)) from error

    def clear(self) -> None:
        if not self._closed:
            self._search.clear()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._search.clear()
        finally:
            self._search.close()
