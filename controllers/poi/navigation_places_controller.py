# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt POI discovery, saved places, and platform actions to UI contracts."""
import math
from dataclasses import replace
import threading
from queue import SimpleQueue, Empty
from collections.abc import Callable
from protocols.map_renderer.map_poi_source import RawMapCamera
from ui.navigation import GeoPoint

from controllers.navigation.map_favorites import MapFavorites
from controllers.poi.poi_search_controller_if import PoiSearchControllerIf
from controllers.poi.poi_action_executor_if import PoiActionExecutorIf
from ui.navigation.navigation_places_request_handler_if import MapFavorite, NavigationPlacesRequestHandlerIf, NavigationCameraState, PlaceActionResult
from ui.navigation.poi_models import PoiAction, PoiActionKind, PoiCategory, PoiSearchResult, PointOfInterest, TransitMode


class NavigationPlacesController(NavigationPlacesRequestHandlerIf):
    """Own one search session while sharing durable favorites and action adapters."""

    def __init__(self, search: PoiSearchControllerIf, favorites: MapFavorites, actions: PoiActionExecutorIf, *, online_allowed: Callable[[], bool] = lambda: True, camera_observer=None, local_3d_action=None):
        self._search = search
        self._favorites = favorites
        self._actions = actions
        self._closed = False
        self._online_allowed = online_allowed
        self._camera_observer = camera_observer
        self._local_3d_action = local_3d_action
        self._action_results = SimpleQueue()
        self._action_lock = threading.Lock()
        self._action_pending = False
        self._action_id = 0

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
        poi = None if self._closed else self._search.poll_selected()
        if not isinstance(poi, PointOfInterest):
            return poi
        latitude = math.degrees(poi.position.latitude_rad)
        longitude = math.degrees(poi.position.longitude_rad)
        if not (math.isfinite(latitude) and math.isfinite(longitude)
                and -90 <= latitude <= 90 and -180 <= longitude <= 180):
            return poi
        action = PoiAction(PoiActionKind.OPEN_WEBSITE, "Explore in Google Earth",
                           provider_id="google-earth-explore",
                           uri=(f"https://earth.google.com/web/@{latitude:.7f},{longitude:.7f},"
                                "0a,1000d,35y,0h,45t,0r"))
        actions = tuple(a for a in poi.actions if a.provider_id != "google-earth-explore")
        actions = actions + (action,)
        if self._local_3d_action is not None:
            local_action = self._local_3d_action(poi)
            if local_action is not None:
                actions = tuple(a for a in actions if a.kind is not PoiActionKind.EXPLORE_3D) + (local_action,)
        return replace(poi, actions=actions)

    def poll_camera_interaction(self) -> bool:
        return False if self._closed else self._search.poll_camera_interaction()

    def execute(self, poi: PointOfInterest, action: PoiAction) -> str:
        if self._closed:
            raise RuntimeError('Navigation places session is closed')
        if action.kind is not PoiActionKind.EXPLORE_3D and not self._online_allowed():
            raise ValueError('Offline mode: go online to order or open websites')
        try:
            return self._actions.execute(poi, action)
        except ValueError:
            raise
        except Exception as error:
            # Frontends handle contract errors without importing Android launcher types.
            raise RuntimeError(str(error)) from error

    def poll_camera_state(self) -> NavigationCameraState | None:
        if self._closed:
            return None
        poll = getattr(self._search, 'poll_camera_state', None)
        raw = poll() if poll else None
        if not isinstance(raw, RawMapCamera):
            return None
        camera = NavigationCameraState(
            GeoPoint(math.radians(raw.latitude), math.radians(raw.longitude)),
            raw.zoom, math.radians(raw.bearing), math.radians(raw.pitch))
        if self._camera_observer is not None:
            self._camera_observer(camera.center, camera.zoom, camera.bearing_rad, camera.pitch_rad)
        return camera

    def request_action(self, poi: PointOfInterest, action: PoiAction) -> int | None:
        with self._action_lock:
            if self._closed or self._action_pending:
                return None
            self._action_pending = True
            self._action_id += 1
            request_id = self._action_id
        def launch():
            try:
                result = PlaceActionResult(request_id, self.execute(poi, action), True)
            except (RuntimeError, ValueError) as error:
                result = PlaceActionResult(request_id, f'Launch failed: {error}', False)
            with self._action_lock:
                self._action_pending = False
                if not self._closed:
                    self._action_results.put(result)
        threading.Thread(target=launch, name='orc-poi-launch', daemon=True).start()
        return request_id

    def poll_action_result(self) -> PlaceActionResult | None:
        if self._closed:
            return None
        try:
            return self._action_results.get_nowait()
        except Empty:
            return None

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
