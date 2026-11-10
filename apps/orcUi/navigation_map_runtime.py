"""Compose native-map and browser-map lifecycle outside the Tk widgets."""

import os
import logging
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from apps.orcUi.map_platform_requests import MapPlatformRequests
from controllers.navigation.earth_navigation_controller import EarthNavigationController
from frontends.x11.x11_window_embedder import X11WindowEmbedder
from protocols.chromium.chromium_devtools_client import ChromiumDevToolsClient
from ui.navigation.map_platform_if import MapPlatform, MapPlatformState

_LOG = logging.getLogger("navigation.earth")


class NavigationMapRuntime:
    """Serialize Earth startup, camera work, detachment, and native fallback."""

    def __init__(self, native, native_requests, earth, *, controller=None, embedder=None,
                 online_allowed=lambda: True, earth_enabled=True) -> None:
        self._native = native
        self._earth = earth
        self._controller = controller or EarthNavigationController()
        self._embedder = embedder or X11WindowEmbedder()
        self._devtools = ChromiumDevToolsClient(port=9223)
        self._online_allowed = online_allowed
        self._earth_enabled = earth_enabled
        self._lock = threading.RLock()
        self._state = MapPlatformState()
        self._host = None
        self._owner = None
        self._size = (800, 600)
        self._embedded_size = None
        self._generation = 0
        self._closed = False
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="earth-map")
        self._stop_tick = threading.Event()
        self.requests = MapPlatformRequests(native_requests, self._send_camera)
        self._controller.start()
        self._ticker = threading.Thread(target=self._tick_loop, daemon=True)
        self._ticker.start()

    @property
    def state(self) -> MapPlatformState:
        with self._lock:
            return self._state

    def set_theme(self, mode) -> None:
        self._native.set_theme(mode)

    def launch(self, parent_window_id: int) -> None:
        with self._lock:
            if self._closed:
                return
            self._host = parent_window_id
            platform = self._state.requested
        if platform is MapPlatform.MAPLIBRE:
            self._native.launch(parent_window_id)
        else:
            self.request_platform(platform)

    def resize(self, width: int, height: int, owner_window_id: int) -> None:
        with self._lock:
            self._size = (max(1, width), max(1, height))
            self._owner = owner_window_id
        # The periodic worker applies the latest size, coalescing resize events.

    def request_platform(self, platform: MapPlatform) -> None:
        platform = MapPlatform(platform)
        with self._lock:
            if self._closed:
                return
            if platform is MapPlatform.EARTH and (not self._earth_enabled or not self._online_allowed()):
                self._state = replace(self._state, status="Earth needs enabled application policy and internet")
                return
            self._generation += 1
            generation = self._generation
            self._state = replace(self._state, requested=platform, busy=True,
                                  status=f"Opening {platform.value}…")
            self._worker.submit(self._select, platform, generation)

    def _current(self, generation) -> bool:
        with self._lock:
            return not self._closed and self._host is not None and generation == self._generation

    def _select(self, platform, generation) -> None:
        if not self._current(generation):
            return
        try:
            if platform is MapPlatform.MAPLIBRE:
                self._hide_earth()
                if not self._current(generation):
                    return
                self._native.launch(self._host)
            else:
                self._native.stop()
                display = os.environ.get("DISPLAY", ":1")
                size = self._size
                # Recreate a blank shell; never reparent an active Earth canvas.
                self._hide_earth()
                self._earth.configure_app_window(position=(-20000, -20000), size=size)
                self._earth.prepare(display)
                if not self._current(generation):
                    self._hide_earth()
                    return
                self._embedder.embed(0, self._host, *size, window_class=self._earth.WINDOW_CLASS)
                self._embedded_size = size
                if not self._current(generation):
                    self._hide_earth()
                    return
                if not self._load_embedded_earth(generation):
                    self._hide_earth()
                    return
                self._controller.reset()
            with self._lock:
                if self._current(generation):
                    self._state = MapPlatformState(platform, platform, False,
                        "Earth — loading GPS bridge; route/POI overlays remain on MapLibre"
                        if platform is MapPlatform.EARTH else "MapLibre")
        except Exception as error:
            self._hide_earth()
            if self._current(generation):
                try:
                    self._native.launch(self._host)
                except (OSError, RuntimeError):
                    pass
                with self._lock:
                    self._state = MapPlatformState(status=f"Earth unavailable: {error}; returned to MapLibre")

    def _load_embedded_earth(self, generation) -> bool:
        deadline = time.monotonic() + 8.0
        last_error = None
        while self._current(generation) and time.monotonic() < deadline:
            try:
                target = next((target for target in self._devtools.targets()
                               if target.url == "about:blank"), None)
                if target is not None:
                    result = self._devtools.command(target, "Page.navigate", {
                        "url": "https://earth.google.com/web"})
                    if result.get("errorText"):
                        raise RuntimeError(result["errorText"])
                    return True
            except (OSError, RuntimeError, ValueError) as error:
                last_error = error
            time.sleep(0.05)
        if self._current(generation):
            raise RuntimeError(f"Earth browser shell did not become ready: {last_error or 'no blank page'}")
        return False

    def _hide_earth(self) -> None:
        self._embedded_size = None
        try:
            if self._earth is not None and self._earth.is_running():
                # Close while still attached, before the transient host dies.
                # Moving/hiding a live Zink surface has failed on Termux/X11.
                self._earth.stop(os.environ.get("DISPLAY", ":1"))
        finally:
            self._embedder.clear()

    def _tick_loop(self) -> None:
        pending = None
        while not self._stop_tick.wait(0.5):
            with self._lock:
                if self._closed:
                    return
                if self._host is None or self._state.busy or self._state.active is not MapPlatform.EARTH:
                    continue
                if pending is None or pending.done():
                    pending = self._worker.submit(self._tick, self._generation)

    def _tick(self, generation) -> None:
        if not self._current(generation):
            return
        try:
            if not self._earth.is_running():
                raise RuntimeError("Earth browser exited")
            size = self._size
            if size != self._embedded_size:
                self._embedder.resize(*size)
                self._embedded_size = size
            self._controller.tick()
            with self._lock:
                if self._current(generation):
                    self._state = replace(self._state, status=(
                        self._controller.status + "; overlays remain on MapLibre"))
        except (OSError, RuntimeError, ValueError) as error:
            if self._current(generation):
                self._select(MapPlatform.MAPLIBRE, generation)
                with self._lock:
                    if self._current(generation):
                        self._state = replace(self._state, status=f"Earth unavailable: {error}; MapLibre")

    def _send_camera(self, name, args, kwargs) -> None:
        with self._lock:
            if not self._closed and self._host is not None and self._state.active is MapPlatform.EARTH:
                self._worker.submit(self._camera_request, self._generation, name, args, kwargs)

    def request_chase(self) -> None:
        self._send_camera("request_chase", (True,), {})

    def _camera_request(self, generation, name, args, kwargs) -> None:
        if self._current(generation) and self.state.active is MapPlatform.EARTH:
            try:
                getattr(self._controller, name)(*args, **kwargs)
            except (OSError, RuntimeError, ValueError) as error:
                with self._lock:
                    if self._current(generation):
                        self._state = replace(self._state, status=f"Earth camera: {error}")

    def stop(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._generation += 1
            self._host = None
            self._state = replace(self._state, busy=False)
            cleanup = self._worker.submit(self._hide_earth)
        # Detach before the frontend destroys its transient native host.
        try:
            cleanup.result()
        finally:
            self._native.stop()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
        try:
            self.stop()
        finally:
            with self._lock:
                self._closed = True
            self._stop_tick.set()
            self._ticker.join()
            try:
                self._worker.shutdown(wait=True, cancel_futures=True)
            finally:
                self._controller.close()
