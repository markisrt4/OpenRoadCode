# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""HOME-screen assembly for the integrated orcUi Tk frontend."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.navigation.map_runtime_if import MapRuntimeIf
from apps.orcUi.frontend.tk.presentation_state import OrcUiPresentationState
from apps.orcUi.navigation_presenter import (
    AttitudePresentationState,
    PositionPresentationState,
)
from apps.orcUi.trip_presenter import TripPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from ui.automotive.automotive_telemetry_profile import (AutomotiveTelemetryProfile)
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.navigation import MapRequestHandlerIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle
from ui.navigation.road_speed_limit_ui_if import RoadSpeedLimitState, RoadSpeedLimitUiIf

from .context_rail import ContextRail
from .home_map_panel import HomeMapPanel
from .shell_content import add_summary, panel


def build_home_screen(
    parent: tk.Frame,
    *,
    map_request_handler: MapRequestHandlerIf,
    theme: ThemeBundle,
    vehicle_state: VehiclePresentationState,
    trip_state: TripPresentationState,
    position_state: PositionPresentationState,
    attitude_state: AttitudePresentationState,
    on_expand_context: Callable[[str], None],
    radio_factory: Callable[[tk.Misc], tk.Widget] | None,
    media_factory: Callable[[tk.Misc], tk.Widget] | None,
    spectrum_factory: Callable[[tk.Misc], tk.Widget] | None = None,
    radar_enabled: Callable[[], bool] = lambda: False,
    on_radar_toggle: Callable[[bool], None] | None = None,
    road_speed_limit: RoadSpeedLimitState = RoadSpeedLimitState(),
) -> tuple[HomeMapPanel, ContextRail]:
    """Build HOME content and return the stateful child widgets."""
    ui = theme.ui
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_columnconfigure(1, weight=0, minsize=ContextRail.WIDTH)
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_rowconfigure(1, weight=0)

    map_panel = HomeMapPanel(
        parent,
        map_request_handler=map_request_handler,
        theme=theme,
        radar_enabled=radar_enabled,
        on_radar_toggle=on_radar_toggle,
    )
    map_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))

    context = ContextRail(parent, on_expand=on_expand_context, theme=theme)
    context.update_vehicle_state(vehicle_state)
    context.set_road_speed_limit(road_speed_limit)
    context.update_trip_state(trip_state)
    context.update_position_state(position_state)
    context.update_attitude_state(attitude_state)
    context.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))

    lower = tk.Frame(parent, bg=ui.background, height=250)
    # Reserve enough room for useful audio controls and the shared analyzer.
    lower.grid_propagate(False)
    lower.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(5, 0))
    lower.grid_columnconfigure(0, weight=1, uniform="home-audio")
    lower.grid_columnconfigure(1, weight=1, uniform="home-audio")
    lower.grid_rowconfigure(0, weight=1)

    radio = panel(lower, "RADIO", ui.accent_warning, theme=theme, compact=True)
    radio.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    if radio_factory is None:
        add_summary(
            radio,
            "No radio active",
            "Choose RF or streaming",
            theme=theme,
        )
    else:
        radio_factory(radio).pack(fill=tk.BOTH, expand=True)

    media = panel(lower, "MEDIA", ui.accent_primary, theme=theme, compact=True)
    media.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    if media_factory is None:
        add_summary(media, "No media", "Playback service", theme=theme)
    else:
        media_factory(media).pack(fill=tk.BOTH, expand=True)

    if spectrum_factory is not None:
        lower.grid_rowconfigure(1, weight=0)
        spectrum_factory(lower).grid(row=1, column=0, columnspan=2,
                                     sticky="ew", padx=10, pady=(2, 0))

    return map_panel, context


class HomeScreen(TkScreen, RoadSpeedLimitUiIf):
    """Own the HOME destination and its transient Tk presentation."""

    SCREEN_ID = ScreenId("HOME")

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        map_runtime: MapRuntimeIf,
        map_request_handler: MapRequestHandlerIf,
        theme_bundle: Callable[[], ThemeBundle],
        presentation: OrcUiPresentationState,
        telemetry_profile_request: (
            Callable[[AutomotiveTelemetryProfile], None] | None
        ),
        on_expand_context: Callable[[str], None],
        radar_enabled: Callable[[], bool] = lambda: False,
        on_radar_toggle: Callable[[bool], None] | None = None,
        refresh_radar: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(self.SCREEN_ID)
        self._host = host
        self._map_runtime = map_runtime
        self._map_request_handler = map_request_handler
        self._theme_bundle = theme_bundle
        self._presentation = presentation
        self._telemetry_profile_request = telemetry_profile_request
        self._on_expand_context = on_expand_context
        self._radar_enabled = radar_enabled
        self._on_radar_toggle = on_radar_toggle
        self._refresh_radar = refresh_radar

        self._radio_factory: Callable[[tk.Misc], tk.Widget] | None = None
        self._media_factory: Callable[[tk.Misc], tk.Widget] | None = None
        self._spectrum_factory: Callable[[tk.Misc], tk.Widget] | None = None
        self._map_panel: HomeMapPanel | None = None
        self._context_rail: ContextRail | None = None
        self._road_speed_limit = RoadSpeedLimitState()

    def set_road_speed_limit(self, state: RoadSpeedLimitState) -> None:
        """Render supplied road state without transport access in Home."""
        self._road_speed_limit = state
        if self._context_rail is not None and self._context_rail.winfo_exists():
            self._context_rail.set_road_speed_limit(state)

    @property
    def context_rail(self) -> ContextRail | None:
        """Return the active HOME context rail, when HOME is displayed."""
        return self._context_rail

    def set_radio_factory(
        self,
        factory: Callable[[tk.Misc], tk.Widget] | None,
    ) -> None:
        """Install the radio-owned HOME presentation factory."""
        self._radio_factory = factory

    def set_spectrum_factory(self, factory: Callable[[tk.Misc], tk.Widget] | None) -> None:
        """Install a shared spectrum strip below both Home audio cards."""
        self._spectrum_factory = factory

    def set_media_factory(
        self,
        factory: Callable[[tk.Misc], tk.Widget] | None,
    ) -> None:
        """Install the media-owned HOME presentation factory."""
        self._media_factory = factory

    def apply_vehicle_state(self, state: VehiclePresentationState) -> None:
        """Refresh the mounted HOME vehicle summary."""
        context = self._context_rail
        if context is not None and context.winfo_exists():
            context.update_vehicle_state(state)

    def apply_trip_state(self, state: TripPresentationState) -> None:
        """Refresh the mounted HOME trip summary."""
        context = self._context_rail
        if context is not None and context.winfo_exists():
            context.update_trip_state(state)

    def apply_position_state(self, state: PositionPresentationState) -> None:
        """Refresh the mounted HOME position summary."""
        context = self._context_rail
        if context is not None and context.winfo_exists():
            context.update_position_state(state)

    def apply_attitude_state(self, state: AttitudePresentationState) -> None:
        """Refresh the mounted HOME attitude summary."""
        context = self._context_rail
        if context is not None and context.winfo_exists():
            context.update_attitude_state(state)

    def show(self) -> None:
        """Build HOME content and start its embedded map renderer."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("")

        self._map_panel, self._context_rail = build_home_screen(
            self._host.screen_parent,
            map_request_handler=self._map_request_handler,
            theme=self._theme_bundle(),
            vehicle_state=self._presentation.vehicle,
            trip_state=self._presentation.trip,
            position_state=self._presentation.position,
            attitude_state=self._presentation.attitude,
            on_expand_context=self._on_expand_context,
            radio_factory=self._radio_factory,
            media_factory=self._media_factory,
            spectrum_factory=self._spectrum_factory,
            radar_enabled=self._radar_enabled,
            on_radar_toggle=self._on_radar_toggle,
            road_speed_limit=self._road_speed_limit,
        )

        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.HOME)

        self._host.screen_parent.update_idletasks()
        self._start_map_renderer()
        if self._refresh_radar is not None:
            for delay_ms in (300, 700, 1200, 2500, 5000, 10000):
                self._host.schedule_ui_callback(delay_ms, self._refresh_map_radar)

    def hide(self) -> None:
        """Stop transient HOME resources when navigating away."""
        self._map_runtime.stop()
        self._map_panel = None
        self._context_rail = None

    def refresh_radar_state(self) -> None:
        """Refresh the mounted Home toggle after shared radar-state changes."""
        panel = self._map_panel
        if panel is not None and panel.winfo_exists():
            panel._render_radar_state()

    def _refresh_map_radar(self) -> None:
        panel = self._map_panel
        if panel is not None and panel.winfo_exists() and self._refresh_radar is not None:
            self._refresh_radar()
            panel._radar_button.lift()

    def _start_map_renderer(self) -> None:
        panel = self._map_panel
        if panel is None:
            return

        try:
            self._map_runtime.launch(panel.map_host_window_id)
        except (OSError, RuntimeError) as error:
            print(
                "WARNING: map renderer: "
                f"{type(error).__name__}: {error}"
            )
