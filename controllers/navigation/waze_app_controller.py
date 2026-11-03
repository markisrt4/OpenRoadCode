# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Open and retain native Waze, reporting failure without switching providers."""
from collections.abc import Callable
from threading import Lock, Thread
import logging
import math
from common.logging.structured import event

from ui.navigation.android_app_view_if import AndroidAppViewRequestHandlerIf
from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf
from ui.navigation.waze_request_handler_if import WazeRequestHandlerIf, WazeSessionState
from ui.navigation import GeoPoint


class WazeAppController(WazeRequestHandlerIf):
    def __init__(self, launcher: InstalledAndroidAppLauncherIf,
                 view: AndroidAppViewRequestHandlerIf, *,
                 dispatch_ui: Callable[[Callable[[], None]], None],
                 online: Callable[[], bool], fallback: Callable[[], None],
                 status: Callable[[str], None], session_changed=lambda _state: None,
                 session_closed=lambda: None):
        self._launcher, self._view = launcher, view
        self._dispatch_ui, self._online = dispatch_ui, online
        self._fallback, self._status = fallback, status
        self._lock = Lock()
        self._closed = False
        self._pending = False
        self._generation = 0
        self._operation_lock = Lock()
        self._session_name = None
        self._state = WazeSessionState()
        self._session_changed = session_changed
        self._session_closed = session_closed

    @property
    def state(self):
        with self._lock:
            return self._state

    def request_open_waze(self):
        self._request_launch()

    def request_navigate_waze(self, destination: GeoPoint):
        lat, lon = destination.latitude_rad, destination.longitude_rad
        if (not math.isfinite(lat) or not math.isfinite(lon)
                or abs(lat) > math.pi / 2 or abs(lon) > math.pi):
            self._status('Waze destination is invalid')
            return
        self._request_launch(f'waze://?ll={math.degrees(lat):.7f},{math.degrees(lon):.7f}&navigate=yes')

    def _request_launch(self, uri=None):
        with self._lock:
            if self._closed:
                return
        if not self._online() and not (self.state.active and uri is None):
            self._status('Waze requires online mode')
            return
        with self._lock:
            if self._closed or self._pending:
                return
            self._pending = True
            self._state = WazeSessionState(self._state.active, launching=True)
            generation = self._generation
        self._status('Opening Waze…')
        Thread(target=self._launch, args=(generation, uri), daemon=True).start()

    def _launch(self, generation, uri=None):
        with self._operation_lock:
            with self._lock:
                if self._closed or generation != self._generation:
                    return
                resume = self._state.active and uri is None
            try:
                if resume:
                    self._launcher.resume_installed_app('com.waze')
                    name = self._session_name
                else:
                    name = (self._launcher.launch_installed_app('com.waze') if uri is None else
                            self._launcher.launch_installed_app('com.waze', uri=uri))
            except (OSError, RuntimeError):
                name = None
        with self._lock:
            if self._closed or generation != self._generation:
                return
        self._dispatch_ui(lambda: self._finish(generation, name, uri is not None))

    def _finish(self, generation, name, navigating=False):
        with self._lock:
            if self._closed or generation != self._generation:
                return
            self._pending = False
            self._state = WazeSessionState(self._state.active)
        if not self._online() and not self.state.active:
            return
        if name:
            with self._lock:
                self._session_name = name
                self._state = WazeSessionState(active=True)
            self._session_changed(self.state)
            event(logging.getLogger('navigation.waze'), logging.INFO,
                  'app.open.requested', 'Opening Waze', backend='native', destination_requested=navigating)
            self._view.request_show_android_app(name, 'com.waze')
        elif self.state.active:
            self._status('Could not restore Waze. Its session is still retained; check the Android connection.')
        elif navigating:
            self._status('Could not send destination to native Waze. Check that Waze is installed and running.')
        else:
            self._fallback()

    def request_close_waze(self):
        with self._lock:
            if self._closed or self._state.closing:
                return
            self._generation += 1
            generation = self._generation
            self._pending = True
            self._state = WazeSessionState(self._state.active, closing=True)
        self._status('Closing Waze…')
        Thread(target=self._stop_session, args=(generation,), daemon=True).start()

    def _stop_session(self, generation):
        error = None
        with self._operation_lock:
            try:
                self._launcher.stop_installed_app('com.waze')
            except (OSError, RuntimeError) as caught:
                error = caught
        self._dispatch_ui(lambda: self._finish_close(generation, error))

    def _finish_close(self, generation, error):
        with self._lock:
            if self._closed or generation != self._generation:
                return
            self._pending = False
            self._state = WazeSessionState(self._state.active if error else False)
            if error is None:
                self._session_name = None
        if error is not None:
            self._status('Could not close Waze. Its session is still retained; check the Android connection and retry.')
            return
        self._view.request_close_android_app()
        self._session_changed(self.state)
        self._session_closed()

    def cancel(self):
        with self._lock:
            if self._state.closing:
                return
            self._generation += 1
            self._pending = False
            self._state = WazeSessionState(self._state.active)

    def close(self):
        with self._lock:
            self._closed = True
            self._generation += 1
            self._pending = False
            self._state = WazeSessionState()
        self._session_changed(self.state)
