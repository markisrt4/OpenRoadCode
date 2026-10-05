# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation-screen lifecycle for the integrated orcUi Tk frontend."""

from __future__ import annotations

from ui.system.online_mode_if import OnlineModeIf
from ui.tooltip_if import TooltipFactoryIf

from collections.abc import Callable

from ui.navigation.map_runtime_if import MapRuntimeIf
from ui.automotive.automotive_telemetry_profile import (AutomotiveTelemetryProfile)
from ui.weather.radar_ui_if import RadarPalette, RadarUiState
from ui.weather.radar_controls_if import RadarControlsIf
from ui.weather.radar_request_handler_if import RadarRequestHandlerIf
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.navigation import (
    MapRequestHandlerIf,
    RouteRequestHandlerIf,
    RouteSimulationRequestHandlerIf,
)
from ui.screen_ui_if import ScreenId
from ui.navigation.navigation_places_request_handler_if import NavigationPlacesFactoryIf, NavigationPlacesRequestHandlerIf
from ui.theme import ThemeBundle

from .navigation_panel import NavigationPanel
from .screen_builders import build_navigation_screen


class NavigationScreen(TkScreen, RadarControlsIf):
    """Own the NAVIGATION destination and its transient map presentation."""

    SCREEN_ID = ScreenId("NAVIGATION")

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        map_runtime: MapRuntimeIf,
        places_factory: NavigationPlacesFactoryIf,
        map_request_handler: MapRequestHandlerIf,
        route_request_handler: RouteRequestHandlerIf,
        route_simulation_handler: RouteSimulationRequestHandlerIf,
        theme_bundle: Callable[[], ThemeBundle],
        telemetry_profile_request: (
            Callable[[AutomotiveTelemetryProfile], None] | None
        ),
        on_back: Callable[[], None],
        route_weather=None,
        online_mode: OnlineModeIf | None = None,
        tooltip_factory: TooltipFactoryIf | None = None,
    ) -> None:
        super().__init__(self.SCREEN_ID)
        if not isinstance(places_factory, NavigationPlacesFactoryIf):
            raise TypeError("Navigation requires NavigationPlacesFactoryIf")
        self._places_factory = places_factory
        self._places_session = None
        self._route_weather = route_weather
        self._online_mode = online_mode
        self._tooltip_factory = tooltip_factory
        self._host = host
        self._map_runtime = map_runtime
        self._map_request_handler = map_request_handler
        self._route_request_handler = route_request_handler
        self._route_simulation_handler = route_simulation_handler
        self._theme_bundle = theme_bundle
        self._telemetry_profile_request = telemetry_profile_request
        self._on_back = on_back
        self._radar_handler: RadarRequestHandlerIf | None = None
        self._radar_state = RadarUiState()
        self._panel: NavigationPanel | None = None

    def _close_places_session(self) -> None:
        session = self._places_session
        self._places_session = None
        if session is not None:
            session.close()

    def set_radar_request_handler(self, handler: RadarRequestHandlerIf | None):
        """Bind radar actions to an explicit UI request contract."""
        if handler is not None and not isinstance(handler, RadarRequestHandlerIf):
            raise TypeError("Radar controls require RadarRequestHandlerIf")
        self._radar_handler = handler

    def set_radar_state(self, state: RadarUiState) -> None:
        """Present a complete snapshot without accessing a weather controller."""
        previous = self._radar_state
        self._radar_state = state
        if self._panel is not None:
            self._panel.apply_radar_state(state)
        if state.status != previous.status:
            self._host.set_screen_status(state.status)

    def show(self) -> None:
        """Build NAVIGATION content and start its embedded map renderer."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("NAVIGATION")

        self._close_places_session()
        session = self._places_factory.create()
        if not isinstance(session, NavigationPlacesRequestHandlerIf):
            raise TypeError("Navigation places require NavigationPlacesRequestHandlerIf")
        self._places_session = session
        try:
            self._panel = build_navigation_screen(
                self._host.screen_parent,
                map_request_handler=self._map_request_handler,
                places_handler=self._places_session,
                online_mode=self._online_mode,
                tooltip_factory=self._tooltip_factory,
                route_request_handler=self._route_request_handler,
                route_simulation_handler=self._route_simulation_handler,
                on_back=self._on_back,
                theme=self._theme_bundle(),
                radar_enabled=self._radar_state.enabled,
                radar_frame_time=self._radar_state.frame_time,
                radar_palette=self._radar_state.palette,
                on_radar_palette_changed=(self._change_radar_palette if self._radar_handler is not None else None),
                on_radar_toggle=self._toggle_radar if self._radar_handler is not None else None,
                on_radar_previous=self._radar_previous if self._radar_handler is not None else None,
                on_radar_next=self._radar_next if self._radar_handler is not None else None,
                on_radar_live=self._radar_live if self._radar_handler is not None else None,
                on_radar_play=self._radar_play_pause,
                on_radar_seek=self._radar_seek,
                on_radar_speed=self._radar_set_speed,
                on_radar_source=self._change_radar_source,
            )
        except Exception:
            self._close_places_session()
            raise
        self.set_radar_state(self._radar_state)
        if self._radar_handler is not None:
            self._radar_handler.request_navigation_visible(True)
        if self.__dict__.get("_route_weather") is not None:
            self._route_weather.attach(self._panel)

        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.BACKGROUND)

        self._host.screen_parent.update_idletasks()
        self._start_map_renderer()
        if self._radar_handler is not None and self._radar_state.enabled:
            for delay_ms in (300, 700, 1200, 2500, 5000, 10000):
                self._host.schedule_ui_callback(delay_ms, self._refresh_map_radar)

    def hide(self) -> None:
        """Stop transient navigation resources when navigating away."""
        if self._radar_handler is not None:
            self._radar_handler.request_navigation_visible(False)
        if self._panel is not None:
            self._panel.close_radar_menu()
            self._panel._sync_renderer_camera()
            self._panel.close_places()
            self._panel.close_tooltips()
        if self.__dict__.get("_route_weather") is not None:
            self._route_weather.hide()
        self._close_places_session()
        self._map_runtime.stop()
        self._panel = None

    def close(self) -> None:
        """Disconnect transient weather widgets when the application exits."""
        if self._panel is not None:
            self._panel._sync_renderer_camera()
            self._panel.close_places()
            self._panel.close_tooltips()
        self._close_places_session()
        self._panel = None
        self._radar_handler = None
        if self.__dict__.get("_route_weather") is not None:
            self._route_weather.close()

    def _refresh_map_radar(self) -> None:
        if self._panel is not None and self._radar_handler is not None:
            self._radar_handler.request_replay()

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

    @property
    def radar_enabled(self) -> bool:
        """Return requested visibility from the most recent UI snapshot."""
        return self._radar_state.enabled

    def set_radar_enabled(self, enabled: bool) -> None:
        """Emit a visibility request shared by Home and Weather shortcuts."""
        if self._radar_handler is not None:
            self._radar_handler.request_enabled(enabled)

    def _toggle_radar(self, enabled):
        self.set_radar_enabled(enabled)

    def _radar_previous(self):
        if self._radar_handler is not None:
            self._radar_handler.request_previous()

    def _radar_next(self):
        if self._radar_handler is not None:
            self._radar_handler.request_next()

    def _radar_live(self):
        if self._radar_handler is not None:
            self._radar_handler.request_live()

    def _radar_seek(self, index):
        if self._radar_handler is not None:
            self._radar_handler.request_seek(index)

    def _radar_play_pause(self):
        if self._radar_handler is not None:
            self._radar_handler.request_play_pause()

    def _radar_set_speed(self, speed):
        if self._radar_handler is not None:
            self._radar_handler.request_speed(speed)

    def _change_radar_palette(self, palette):
        if self._radar_handler is not None:
            self._radar_handler.request_palette(palette)

    def _change_radar_source(self, forecast):
        if self._radar_handler is not None:
            self._radar_handler.request_source(forecast)
