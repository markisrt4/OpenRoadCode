# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Queue worker presentation requests and host the dedicated Weston surface."""
from threading import Lock
from dataclasses import replace

from apps.orcUi.adapters.waydroid_surface_player import WaydroidSurfacePlayer
from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.media.android_app_screen import AndroidAppScreen
from frontends.x11.waydroid_window_embedder import WaydroidWindowEmbedder
from ui.navigation.android_app_view_if import AndroidAppViewRequestHandlerIf, AndroidAppViewState


class AndroidAppView(AndroidAppViewRequestHandlerIf):
    """Keep Tk calls on the UI thread and reject completions after shutdown."""

    def __init__(self, app, *, map_runtime, map_platform, map_presentation=None,
                 player=None, window_embedder=None, preserve_external_window=True):
        self._app = app
        self._lock = Lock()
        self._closed = False
        self._state = AndroidAppViewState()
        self._player = player if player is not None else WaydroidSurfacePlayer()
        self._screen = AndroidAppScreen(
            'android-app', app, title='Android app', player=self._player,
            default_target='android', window_class=self._player.window_class,
            back_action=lambda: app.navigate_to('NAVIGATION'),
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_request_handler=self._player, preserve_external_window=preserve_external_window,
            surface_geometry=self._player,
            window_embedder=window_embedder if window_embedder is not None else WaydroidWindowEmbedder(),
            window_name=lambda: getattr(self._player, 'window_name', None),
            map_runtime=map_runtime, map_platform=map_platform, requests=self,
            map_presentation=map_presentation,
            breadcrumb=lambda name: app.set_breadcrumb('NAV', name))
        app.register_screen('ANDROID_APP', self._screen, show_in_navigation=False)

    def request_show_android_app(self, app_name='Android app', package=''):
        with self._lock:
            if not self._closed:
                navigation_app = package == 'com.waze'
                state = AndroidAppViewState(app_name.strip() or 'Android app', package,
                                            expanded=navigation_app, can_split=not navigation_app)
                self._app.dispatch_ui(lambda: self._show(state))

    def _show(self, state):
        if self._closed:
            return
        self._state = state
        self._screen.present(state)
        self._app.navigate_to('ANDROID_APP')

    def request_toggle_android_app_expanded(self):
        if not self._closed and self._state.can_split:
            self._state = replace(self._state, expanded=not self._state.expanded)
            self._screen.present(self._state)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._screen.hide()
