# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Construct backend resources for contract-bound navigation places views."""
from collections.abc import Callable
from weakref import WeakSet

from apps.launchers.android_app_launcher import AndroidAppLauncher
from controllers.navigation.map_favorites import MapFavorites
from controllers.poi.android_poi_action_executor import AndroidPoiActionExecutor
from controllers.poi.navigation_places_controller import NavigationPlacesController
from controllers.poi.poi_search_controller import PoiSearchController
from controllers.poi.poi_search_controller_if import PoiSearchControllerIf
from controllers.poi.poi_action_executor_if import PoiActionExecutorIf
from ui.navigation.navigation_places_request_handler_if import NavigationPlacesFactoryIf


class NavigationPlacesFactory(NavigationPlacesFactoryIf):
    """Share durable dependencies and track transient sessions for shutdown."""

    def __init__(self, *, favorites: MapFavorites | None = None,
                 actions: PoiActionExecutorIf | None = None,
                 search_factory: Callable[[], PoiSearchControllerIf] = PoiSearchController,
                 online_allowed: Callable[[], bool] = lambda: True, camera_observer=None):
        self._favorites = favorites if favorites is not None else MapFavorites()
        self._actions = actions if actions is not None else AndroidPoiActionExecutor(AndroidAppLauncher())
        self._search_factory = search_factory
        self._sessions = WeakSet()
        self._closed = False
        self._online_allowed = online_allowed
        self._camera_observer = camera_observer

    def create(self) -> NavigationPlacesController:
        if self._closed:
            raise RuntimeError('Navigation places factory is closed')
        # Match the previous per-mount store construction: pick up saved-place edits.
        self._favorites.load()
        session = NavigationPlacesController(self._search_factory(), self._favorites, self._actions,
                                             online_allowed=self._online_allowed, camera_observer=self._camera_observer)
        self._sessions.add(session)
        return session

    def close(self) -> None:
        """Close every surviving session even when one cleanup fails."""
        if self._closed:
            return
        self._closed = True
        error = None
        for session in list(self._sessions):
            try:
                session.close()
            except Exception as caught:
                error = error or caught
        self._sessions.clear()
        if error is not None:
            raise error
