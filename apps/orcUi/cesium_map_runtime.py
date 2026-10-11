"""Serialize optional embedded Cesium exploration and native-map fallback."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import math
import threading

from ui.navigation import GeoPoint
from ui.navigation.cesium_viewer_state import CesiumViewerState
from ui.navigation.map_platform_if import MapPlatform, MapPlatformState

_PLATFORMS = (MapPlatform.MAPLIBRE, MapPlatform.CESIUM)


class CesiumMapRuntime:
    """Composition-owned lifecycle adapter; no browser access from widgets."""

    def __init__(self, native, viewer, *, initial_view=None):
        self._native, self._viewer = native, viewer
        self._initial_view = initial_view or (lambda: CesiumViewerState(GeoPoint(math.radians(42.3314),math.radians(-83.0458))))
        self._view = None
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
            elif self._current(generation):
                self._native.launch(self._host)
            with self._lock:
                if self._current(generation):
                    self._state = MapPlatformState(platform,platform,False,
                        '3D exploration · routes and radar use MapLibre' if platform is MapPlatform.CESIUM else 'MapLibre',
                        available_platforms=_PLATFORMS)
        except Exception as error:
            try:
                self._viewer.close()
            finally:
                if self._current(generation):
                    self._fallback(generation,f'3D map unavailable: {error}')

    def _fallback(self, generation, status):
        if not self._current(generation):
            return
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
        except Exception as error:
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
