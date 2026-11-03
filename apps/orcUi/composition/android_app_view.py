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
                 player=None, window_embedder=None, preserve_external_window=True,
                 visibility_changed=None, screen_label='ANDROID_APP', navigation_label=None,
                 persistent_session=False, close_action=None, saved_destination_action=None):
        self._app = app
        self._lock = Lock()
        self._closed = False
        self._generation = 0
        self._visibility_changed = visibility_changed
        self._screen_label = screen_label
        self._saved_destination_action = saved_destination_action
        self._state = AndroidAppViewState()
        self._player = player if player is not None else WaydroidSurfacePlayer()
        self._screen = AndroidAppScreen(
            screen_label.lower().replace('_', '-'), app, title='Android app', player=self._player,
            default_target='android', window_class=self._player.window_class,
            back_action=lambda: app.navigate_to('NAVIGATION'),
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_request_handler=self._player, preserve_external_window=preserve_external_window,
            keep_player_on_hide=persistent_session, close_action=close_action,
            surface_geometry=self._player,
            window_embedder=window_embedder if window_embedder is not None else WaydroidWindowEmbedder(),
            window_name=lambda: getattr(self._player, 'window_name', None),
            map_runtime=map_runtime, map_platform=map_platform, requests=self,
            map_presentation=map_presentation,
            breadcrumb=lambda name: app.set_breadcrumb('NAV', name))
        options = {'navigation_label': navigation_label} if navigation_label is not None else {}
        app.register_screen(screen_label, self._screen, show_in_navigation=False, **options)

    def request_show_android_app(self, app_name='Android app', package=''):
        with self._lock:
            if not self._closed:
                navigation_app = package == 'com.waze'
                state = AndroidAppViewState(app_name.strip() or 'Android app', package,
                    expanded=navigation_app, can_split=not navigation_app,
                    can_navigate_saved_destinations=navigation_app and self._saved_destination_action is not None)
                generation = self._generation
                self._app.dispatch_ui(lambda: self._show(state, generation))

    def _show(self, state, generation):
        if self._closed or generation != self._generation:
            return
        self._state = state
        self._screen.present(state)
        self._app.navigate_to(self._screen_label)

    def request_toggle_android_app_expanded(self):
        if not self._closed and self._state.can_split:
            self._state = replace(self._state, expanded=not self._state.expanded)
            self._screen.present(self._state)

    def request_navigate_saved_destination(self, key):
        if not self._closed and self._saved_destination_action is not None:
            self._saved_destination_action(key)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
        if self._visibility_changed is not None:
            self._visibility_changed(False)
        self._screen.close_session()

    def request_close_android_app(self):
        if not self._closed:
            with self._lock:
                self._generation += 1
            self._screen.close_session()

    def request_set_android_app_visible(self, visible):
        if not self._closed and self._visibility_changed is not None:
            self._visibility_changed(visible)
