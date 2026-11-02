# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Queue worker presentation requests and host the dedicated Weston surface."""
from threading import Lock

from apps.orcUi.adapters.waydroid_surface_player import WaydroidSurfacePlayer
from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.media.browser_media_screen import BrowserMediaScreen
from ui.navigation.android_app_view_if import AndroidAppViewRequestHandlerIf


class AndroidAppView(AndroidAppViewRequestHandlerIf):
    """Keep Tk calls on the UI thread and reject completions after shutdown."""

    def __init__(self, app):
        self._app = app
        self._lock = Lock()
        self._closed = False
        self._player = WaydroidSurfacePlayer()
        self._screen = BrowserMediaScreen(
            'android-app', app, title='Android app', player=self._player,
            default_target='android', window_class=self._player.window_class,
            back_action=lambda: app.navigate_to('NAVIGATION'),
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_request_handler=self._player, preserve_external_window=True)
        app.register_screen('ANDROID_APP', self._screen, show_in_navigation=False)

    def request_show_android_app(self):
        with self._lock:
            if not self._closed:
                self._app.dispatch_ui(self._show)

    def _show(self):
        if self._closed:
            return
        self._app.navigate_to('ANDROID_APP')

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._screen.hide()
