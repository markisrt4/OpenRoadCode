"""Serialize optional embedded Cesium exploration and native-map fallback."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import math
import logging
import threading
import time

from ui.navigation import GeoPoint
from ui.navigation.cesium_viewer_state import CesiumViewerState
from ui.navigation.map_platform_if import MapPlatform, MapPlatformState, ExplorationCameraAction
from ui.navigation.poi_overlay_state import PoiOverlayState

_PLATFORMS = (MapPlatform.MAPLIBRE, MapPlatform.CESIUM)


class CesiumMapRuntime:
    """Composition-owned lifecycle adapter; no browser access from widgets."""

    def __init__(self, native, viewer, *, initial_view=None):
        self._native, self._viewer = native, viewer
        self._initial_view = initial_view or (lambda: CesiumViewerState(GeoPoint(math.radians(42.3314),math.radians(-83.0458)), label="3D map", destination_marker_visible=False))
        self._view = None
        self._position = None
        self._position_received = 0.0
        self._position_revision = 0
        self._poll_timeouts = 0
        self._sent_position = None
        self._poi_overlay = PoiOverlayState()
        self._sent_poi_overlay = None
        self._follow_enabled = True
        self._lock = threading.RLock()
        self._state = MapPlatformState(available_platforms=_PLATFORMS)
        self._host = None
        self._size = (800,600)
        self._generation = 0
        self._closed = False
        self._worker = ThreadPoolExecutor(max_workers=1,thread_name_prefix='cesium-map')
        self._stop_tick = threading.Event()
        self._ticker = threading.Thread(target=self._tick_loop,name='cesium-map-watch',daemon=True)
        self._ticker.start()

    @property
    def state(self):
        with self._lock:
            return self._state

    def set_theme(self, mode):
        self._native.set_theme(mode)

    def resize(self, width, height, owner_window_id):
        with self._lock:
            self._size = (max(1,width),max(1,height))

    def launch(self, parent_window_id):
        with self._lock:
            if self._closed:
                return
            self._host = parent_window_id
            platform = self._state.requested
        if platform is MapPlatform.MAPLIBRE:
            self._native.launch(parent_window_id)
        else:
            self.request_platform(platform)

    def request_explore(self, state):
        if not isinstance(state,CesiumViewerState):
            raise TypeError('3D exploration requires CesiumViewerState')
        with self._lock:
            if self._closed or self._host is None:
                raise RuntimeError('Open Navigation before exploring the 3D map')
            self._view = state
            self._follow_enabled = False
            self.request_platform(MapPlatform.CESIUM)

    def request_platform(self, platform):
        platform = MapPlatform(platform)
        if platform not in _PLATFORMS:
            raise ValueError('This prototype supports MapLibre and the local 3D map')
        with self._lock:
            if self._closed or self._host is None:
                return
            if platform is MapPlatform.CESIUM and self._view is None:
                self._view = self._initial_view()
            self._generation += 1
            generation = self._generation
            self._state = replace(self._state,requested=platform,busy=True,status=f'Opening {platform.value}…')
            self._worker.submit(self._select,platform,generation)

    def request_chase(self):
        """Live vehicle-follow is outside this destination-exploration prototype."""

    def request_camera(self, action):
        action = ExplorationCameraAction(action)
        with self._lock:
            if self._closed or self._state.busy or self._state.active is not MapPlatform.CESIUM:
                return
            if action is ExplorationCameraAction.RECENTER:
                self._follow_enabled = True
            elif action not in (ExplorationCameraAction.ZOOM_IN, ExplorationCameraAction.ZOOM_OUT):
                self._follow_enabled = False
            self._state = replace(self._state, follow_enabled=self._follow_enabled)
            self._worker.submit(self._camera, action, self._generation)

    def update_position(self, position):
        """Receive a live SI fix from composition without transport or GUI access."""
        if position is not None and (not isinstance(position, GeoPoint)
                or not math.isfinite(position.latitude_rad) or not math.isfinite(position.longitude_rad)
                or abs(position.latitude_rad) > math.pi/2 or abs(position.longitude_rad) > math.pi):
            raise ValueError('Invalid vehicle position')
        with self._lock:
            if self._closed:
                return
            self._position = position
            self._position_received = time.monotonic()
            self._position_revision += 1

    def update_poi_overlay(self, state):
        """Cache one semantic marker snapshot and update the active 3D renderer."""
        if not isinstance(state, PoiOverlayState):
            raise TypeError('3D POI overlay requires PoiOverlayState')
        with self._lock:
            if self._closed:
                return
            self._poi_overlay = state
            generation = self._generation
            active = self._state.active is MapPlatform.CESIUM and not self._state.busy
        if active:
            self._worker.submit(self._send_poi_overlay, generation)

    def _send_poi_overlay(self, generation):
        with self._lock:
            if not self._current(generation):
                return
            state = self._poi_overlay
        if state != self._sent_poi_overlay:
            try:
                self._viewer.update_poi_overlay(state)
                self._sent_poi_overlay = state
            except (OSError, RuntimeError, ValueError, TypeError) as error:
                with self._lock:
                    if self._current(generation):
                        self._state = replace(self._state, status=f'3D POIs unavailable: {error}')

    def request_follow(self, enabled):
        if type(enabled) is not bool:
            raise TypeError('Follow enabled must be a boolean')
        with self._lock:
            if self._closed:
                return
            self._follow_enabled = enabled
            self._state = replace(self._state, follow_enabled=enabled)

    def _send_position(self, generation):
        with self._lock:
            if not self._current(generation):
                return
            point = self._position if time.monotonic()-self._position_received <= 10 else None
            follow = self._follow_enabled
            key = (self._position_revision if point is not None else None, follow)
        if key != self._sent_position:
            self._viewer.update_position(point, follow)
            self._sent_position = key
        with self._lock:
            if not self._current(generation) or self._follow_enabled != follow:
                return
            self._state = replace(self._state, follow_enabled=follow, position_available=point is not None,
                status='Waiting for live vehicle position' if follow and point is None else
                    '3D map · vehicle follow' if follow else '3D map · exploration')

    def _camera(self, action, generation):
        if not self._current(generation):
            return
        try:
            if action is ExplorationCameraAction.RECENTER:
                self._poll_timeouts = 0
                self._sent_position = None
                self._send_position(generation)
                if self._state.position_available:
                    return
            self._viewer.request_camera(action)
        except Exception as error:
            with self._lock:
                if self._current(generation):
                    self._state = replace(self._state, status=f'3D camera unavailable: {error}')

    def _current(self, generation):
        with self._lock:
            return not self._closed and self._host is not None and generation == self._generation

    def _select(self, platform, generation):
        if not self._current(generation):
            return
        try:
            self._viewer.close()
            if platform is MapPlatform.CESIUM:
                self._native.stop()
                self._viewer.open(self._view,self._host,self._size,lambda:self._current(generation))
                self._sent_position = None
                self._sent_poi_overlay = None
                self._send_poi_overlay(generation)
            elif self._current(generation):
                self._native.launch(self._host)
            with self._lock:
                if self._current(generation):
                    self._state = MapPlatformState(platform,platform,False,
                        '3D exploration · routes and radar use MapLibre' if platform is MapPlatform.CESIUM else 'MapLibre',
                        available_platforms=_PLATFORMS, follow_enabled=self._follow_enabled)
        except Exception as error:
            try:
                self._viewer.close()
            finally:
                if self._current(generation):
                    self._fallback(generation,f'3D map unavailable: {error}')

    def _fallback(self, generation, status):
        if not self._current(generation):
            return
        logging.getLogger(__name__).warning('3D map returned to Map: %s', status)
        try:
            self._native.launch(self._host)
        except (OSError, RuntimeError) as error:
            status += f'; MapLibre failed: {error}'
        with self._lock:
            if self._current(generation):
                self._state = MapPlatformState(status=status,available_platforms=_PLATFORMS)

    def _tick_loop(self):
        pending = None
        while not self._stop_tick.wait(.5):
            with self._lock:
                if self._closed:
                    return
                if self._host is not None and not self._state.busy and self._state.active is MapPlatform.CESIUM:
                    if pending is None or pending.done():
                        pending = self._worker.submit(self._tick,self._generation)

    def _tick(self, generation):
        if not self._current(generation):
            return
        try:
            if not self._viewer.tick(self._size):
                self._viewer.close()
                self._fallback(generation,'MapLibre')
            else:
                if self._viewer.consume_manual_camera() is True:
                    self.request_follow(False)
                self._send_position(generation)
                self._poll_timeouts = 0
        except Exception as error:
            if isinstance(error, TimeoutError) and self._current(generation):
                self._poll_timeouts += 1
                if self._poll_timeouts < 3:
                    with self._lock:
                        if self._current(generation):
                            self._state = replace(self._state, status='3D map busy · retrying browser connection…')
                    return
            try:
                self._viewer.close()
            finally:
                self._fallback(generation,f'3D map unavailable: {error}')

    def stop(self):
        with self._lock:
            if self._closed:
                return
            self._generation += 1
            self._host = None
            self._state = MapPlatformState(available_platforms=_PLATFORMS)
            cleanup = self._worker.submit(self._viewer.close)
        try:
            cleanup.result()
        finally:
            self._native.stop()

    def close(self):
        with self._lock:
            if self._closed:
                return
        try:
            self.stop()
        finally:
            with self._lock:
                self._closed = True
            self._stop_tick.set()
            self._ticker.join(timeout=2)
            self._worker.shutdown(wait=True,cancel_futures=True)
