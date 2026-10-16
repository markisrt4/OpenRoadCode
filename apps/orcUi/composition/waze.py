# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compose an independent, experimental Waze Live Map browser surface."""

from collections.abc import Callable
from dataclasses import dataclass, field

from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
from apps.orcUi.application_runtime import OrcUiApplicationRuntime
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from common.resource_cleanup import ResourceCleanup, close_resources
from frontends.tk.media.browser_media_screen import BrowserMediaScreen


@dataclass(slots=True)
class WazeComposition:
    screen: BrowserMediaScreen
    unsubscribe: Callable[[], None]
    _closed: bool = field(default=False, init=False)

    def close(self) -> None:
        """Cancel pending display callbacks and stop the owned browser once."""
        if self._closed:
            return
        self._closed = True
        close_resources(self.unsubscribe, self.screen.hide)


def configure_waze(app: OrcUiApp, runtime: OrcUiApplicationRuntime) -> WazeComposition | None:
    """Reuse browser lifecycle and presentation without sharing ORC map data."""
    if not runtime.waze_url:
        return None
    with ResourceCleanup() as cleanup:
        player = ManagedBrowserMediaPlayer(
            runtime.manager, "waze", resolve_target=lambda target: target,
            network_allowed=lambda: app.online_mode.online,
        )
        screen = BrowserMediaScreen(
            "waze", app, title="Waze Live Map (experimental)", player=player,
            default_target=runtime.waze_url, window_class="openroadcode-waze",
            back_action=lambda: app.navigate_to("HOME"),
            theme_bundle=lambda: theme_bundle(app.theme_mode),
        )
        cleanup.callback(screen.hide)

        def mode_changed(online: bool) -> None:
            if not online:
                screen.hide()

        unsubscribe = app.online_mode.subscribe(mode_changed)
        cleanup.callback(unsubscribe)
        app.register_screen("WAZE", screen, before="NAVIGATION")
        composition = WazeComposition(screen, unsubscribe)
        cleanup.release()
        return composition
