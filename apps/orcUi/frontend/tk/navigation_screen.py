# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation-screen lifecycle for the integrated orcUi Tk frontend."""

from __future__ import annotations

from collections.abc import Callable
import threading

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
        radar_controller=None,
    ) -> None:
        super().__init__(self.SCREEN_ID)
        self._host = host
        self._map_runtime = map_runtime
        self._map_request_handler = map_request_handler
        self._theme_bundle = theme_bundle
        self._telemetry_profile_request = telemetry_profile_request
        self._on_back = on_back
        self._radar_controller = radar_controller
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
            radar_enabled=(self._radar_controller.enabled if self._radar_controller is not None else False),
            radar_frame_time=(self._radar_controller.frame_time if self._radar_controller is not None else None),
            on_radar_toggle=self._toggle_radar if self._radar_controller is not None else None,
        )

        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.BACKGROUND)

        self._host.screen_parent.update_idletasks()
        self._start_map_renderer()
        if self._radar_controller is not None and self._radar_controller.enabled:
            for delay_ms in (300, 700, 1200):
                self._host.schedule_ui_callback(delay_ms, self._radar_controller.refresh_renderer_state)

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

    def _toggle_radar(self, enabled: bool) -> None:
        controller = self._radar_controller
        if controller is None:
            return
        if not enabled:
            controller.hide()
            return

        def load_latest() -> None:
            try:
                frame = controller.show_latest()
                panel = self._panel
                if panel is not None:
                    self._host.schedule_ui_callback(
                        0,
                        lambda: panel.set_radar_frame_time(frame.timestamp),
                    )
            except Exception as error:
                print(f"WARNING: weather radar: {type(error).__name__}: {error}")

        threading.Thread(target=load_latest, name="weather-radar-refresh", daemon=True).start()
