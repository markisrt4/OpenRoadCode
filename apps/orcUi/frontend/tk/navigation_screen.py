# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation-screen lifecycle for the integrated orcUi Tk frontend."""

from __future__ import annotations

from collections.abc import Callable

from apps.orcUi.core_runtime import MapRuntimeIf
from controllers.automotive import AutomotiveTelemetryProfile
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.navigation import MapRequestHandlerIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle

from .navigation_panel import NavigationPanel
from .screen_builders import build_navigation_screen


class NavigationScreen(TkScreen):
    """Own the NAVIGATION destination and its transient map presentation."""

    SCREEN_ID = ScreenId("NAVIGATION")

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        map_runtime: MapRuntimeIf,
        map_request_handler: MapRequestHandlerIf,
        theme_bundle: Callable[[], ThemeBundle],
        telemetry_profile_request: (
            Callable[[AutomotiveTelemetryProfile], None] | None
        ),
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(self.SCREEN_ID)
        self._host = host
        self._map_runtime = map_runtime
        self._map_request_handler = map_request_handler
        self._theme_bundle = theme_bundle
        self._telemetry_profile_request = telemetry_profile_request
        self._on_back = on_back
        self._panel: NavigationPanel | None = None

    def show(self) -> None:
        """Build NAVIGATION content and start its embedded map renderer."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("NAVIGATION")

        self._panel = build_navigation_screen(
            self._host.screen_parent,
            map_request_handler=self._map_request_handler,
            on_back=self._on_back,
            theme=self._theme_bundle(),
        )

        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.BACKGROUND)

        self._host.screen_parent.update_idletasks()
        self._start_map_renderer()

    def hide(self) -> None:
        """Stop transient navigation resources when navigating away."""
        self._map_runtime.stop()
        self._panel = None

    def _start_map_renderer(self) -> None:
        panel = self._panel
        if panel is None:
            return

        try:
            self._map_runtime.launch(panel.map_host_window_id)
        except (OSError, RuntimeError) as error:
            print(
                "WARNING: map renderer: "
                f"{type(error).__name__}: {error}"
            )
