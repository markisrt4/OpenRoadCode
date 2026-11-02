# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Open native Waze asynchronously, preserving the existing web fallback."""
from collections.abc import Callable
from threading import Lock, Thread
import logging
from common.logging.structured import event

from ui.navigation.android_app_view_if import AndroidAppViewRequestHandlerIf
from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf
from ui.navigation.waze_request_handler_if import WazeRequestHandlerIf


class WazeAppController(WazeRequestHandlerIf):
    def __init__(self, launcher: InstalledAndroidAppLauncherIf,
                 view: AndroidAppViewRequestHandlerIf, *,
                 dispatch_ui: Callable[[Callable[[], None]], None],
                 online: Callable[[], bool], fallback: Callable[[], None],
                 status: Callable[[str], None]):
        self._launcher, self._view = launcher, view
        self._dispatch_ui, self._online = dispatch_ui, online
        self._fallback, self._status = fallback, status
        self._lock = Lock()
        self._closed = False
        self._pending = False
        self._generation = 0

    def request_open_waze(self):
        with self._lock:
            if self._closed:
                return
        if not self._online():
            self._status('Waze requires online mode')
            return
        with self._lock:
            if self._closed or self._pending:
                return
            self._pending = True
            generation = self._generation
        self._status('Opening Waze…')
        Thread(target=self._launch, args=(generation,), daemon=True).start()

    def _launch(self, generation):
        try:
            name = self._launcher.launch_installed_app('com.waze')
        except (OSError, RuntimeError):
            name = None
        with self._lock:
            if self._closed or generation != self._generation:
                return
        self._dispatch_ui(lambda: self._finish(generation, name))

    def _finish(self, generation, name):
        with self._lock:
            if self._closed or generation != self._generation:
                return
            self._pending = False
        if not self._online():
            return
        if name:
            event(logging.getLogger('navigation.waze'), logging.INFO,
                  'app.open.requested', 'Opening Waze', backend='native')
            self._view.request_show_android_app(name, 'com.waze')
        else:
            self._fallback()

    def cancel(self):
        with self._lock:
            self._generation += 1
            self._pending = False

    def close(self):
        with self._lock:
            self._closed = True
            self._generation += 1
            self._pending = False
