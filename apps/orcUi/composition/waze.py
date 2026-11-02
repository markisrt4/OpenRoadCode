# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compose an independent, experimental Waze Live Map browser surface."""

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from common.logging.structured import event
from controllers.navigation.waze_location_player import WazeLocationPlayer
from controllers.navigation.waze_app_controller import WazeAppController
from apps.launchers.installed_waydroid_app import InstalledWaydroidAppLauncher
from ui.navigation.android_app_view_if import AndroidAppViewRequestHandlerIf
from ui.navigation.installed_android_app_if import InstalledAndroidAppLauncherIf
from ui.navigation import GeoPoint
from ui.theme import ThemeMode
from ui.navigation.waze_request_handler_if import WazeRequestHandlerIf

from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
from apps.orcUi.application_runtime import OrcUiApplicationRuntime
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from common.resource_cleanup import ResourceCleanup, close_resources
from frontends.tk.media.browser_media_screen import BrowserMediaScreen


@dataclass(slots=True)
class WazeComposition(WazeRequestHandlerIf):
    screen: BrowserMediaScreen
    unsubscribe: Callable[[], None]
    open_waze: Callable[[], None] = lambda: None
    location: WazeLocationPlayer | None = None
    native: WazeAppController | None = None
    _closed: bool = field(default=False, init=False)

    def request_open_waze(self) -> None:
        if not self._closed:
            self.open_waze()

    def update_position(self, point: GeoPoint | None) -> None:
        if self.location is not None:
            self.location.update_position(point)

    def close(self) -> None:
        """Cancel pending display callbacks and stop the owned browser once."""
        if self._closed:
            return
        self._closed = True
        close_resources(self.native.close if self.native is not None else lambda: None,
                        self.unsubscribe, self.screen.hide,
                        self.location.close if self.location is not None else lambda: None)


def configure_waze(app: OrcUiApp, runtime: OrcUiApplicationRuntime, *,
                   android_app_view: AndroidAppViewRequestHandlerIf | None = None,
                   native_launcher: InstalledAndroidAppLauncherIf | None = None) -> WazeComposition | None:
    """Reuse browser lifecycle and presentation without sharing ORC map data."""
    if not runtime.waze_url:
        return None
    with ResourceCleanup() as cleanup:
        color_scheme = lambda: "dark" if app.theme_mode is ThemeMode.DARK else "light"
        player = ManagedBrowserMediaPlayer(
            runtime.manager, "waze", resolve_target=lambda target: target,
            network_allowed=lambda: app.online_mode.online,
            preferred_color_scheme=color_scheme,
        )
        location = WazeLocationPlayer(player, preferred_color_scheme=color_scheme)
        cleanup.callback(location.close)
        screen = BrowserMediaScreen(
            "waze", app, title="Waze Live Map (experimental)", player=location,
            default_target=runtime.waze_url, window_class="openroadcode-waze",
            back_action=lambda: app.navigate_to("NAVIGATION"),
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_request_handler=location,
            back_label='‹ BACK TO MAP',
        )
        cleanup.callback(screen.hide)

        native = None

        def mode_changed(online: bool) -> None:
            if not online:
                screen.hide()
                if native is not None:
                    native.cancel()

        unsubscribe = app.online_mode.subscribe(mode_changed)
        cleanup.callback(unsubscribe)
        app.register_screen("WAZE", screen, show_in_navigation=False)

        def open_waze() -> None:
            if app.online_mode.online:
                event(logging.getLogger('navigation.waze'), logging.INFO,
                      'app.open.requested', 'Opening Waze', backend='browser')
                app.navigate_to("WAZE")
            else:
                app.set_screen_status("Waze requires online mode")

        if android_app_view is not None:
            native = WazeAppController(native_launcher if native_launcher is not None else InstalledWaydroidAppLauncher(), android_app_view,
                dispatch_ui=app.dispatch_ui, online=lambda: app.online_mode.online,
                fallback=open_waze, status=app.set_screen_status)
            cleanup.callback(native.close)
        composition = WazeComposition(screen, unsubscribe,
                                      native.request_open_waze if native is not None else open_waze,
                                      location, native)
        cleanup.release()
        return composition
