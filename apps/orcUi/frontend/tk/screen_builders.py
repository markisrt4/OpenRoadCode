# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Built-in orcUi screen constructors."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from apps.orcUi.trip_presenter import TripPresentationState
from common.units import UnitSystem
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from controllers.weather.radar_palette import RadarPalette
from controllers.automotive import (
    AutomotiveTelemetryProfile,
    EngineAnalysis,
    VehicleConfiguration,
)
from ui.navigation import MapRequestHandlerIf
from ui.theme import ThemeBundle

from .navigation_panel import NavigationPanel
from .settings_panel import SettingsPanel
from .shell_content import panel
from .vehicle_panel import VehiclePanel


def build_navigation_screen(
    parent: tk.Misc,
    *,
    map_request_handler: MapRequestHandlerIf,
    on_back: Callable[[], None],
    theme: ThemeBundle,
    radar_enabled: bool = False,
    radar_frame_time: int | None = None,
    radar_palette: RadarPalette = RadarPalette.UNIVERSAL,
    on_radar_palette_changed: Callable[[RadarPalette], None] | None = None,
    on_radar_toggle: Callable[[bool], None] | None = None,
    on_radar_previous: Callable[[], None] | None = None,
    on_radar_next: Callable[[], None] | None = None,
    on_radar_live: Callable[[], None] | None = None,
) -> NavigationPanel:
    screen = NavigationPanel(
        parent,
        map_request_handler=map_request_handler,
        on_back=on_back,
        theme_bundle=theme,
        radar_enabled=radar_enabled,
        radar_frame_time=radar_frame_time,
        radar_palette=radar_palette,
        on_radar_palette_changed=on_radar_palette_changed,
        on_radar_toggle=on_radar_toggle,
        on_radar_previous=on_radar_previous,
        on_radar_next=on_radar_next,
        on_radar_live=on_radar_live,
    )
    screen.pack(fill=tk.BOTH, expand=True)
    return screen


def build_vehicle_screen(
    parent: tk.Misc,
    *,
    on_back: Callable[[], None],
    on_view_changed: Callable[[str], None] | None = None,
    on_telemetry_profile: Callable[[AutomotiveTelemetryProfile], None] | None,
    state: VehiclePresentationState,
    trip_state: TripPresentationState,
    theme: ThemeBundle,
    vehicle_configuration: VehicleConfiguration,
    engine_analysis: EngineAnalysis,
) -> VehiclePanel:
    screen = VehiclePanel(
        parent,
        on_back=on_back,
        on_view_changed=on_view_changed,
        on_telemetry_profile=on_telemetry_profile,
        state=state,
        trip_state=trip_state,
        theme_bundle=theme,
        vehicle_configuration=vehicle_configuration,
        engine_analysis=engine_analysis,
    )
    screen.pack(fill=tk.BOTH, expand=True)
    return screen


def build_settings_screen(
    parent: tk.Misc,
    *,
    vehicle_configuration: VehicleConfiguration,
    on_vehicle_configuration_changed: Callable[[VehicleConfiguration], None],
    unit_system: UnitSystem,
    on_unit_system_changed: Callable[[UnitSystem], None],
    on_back: Callable[[], None],
    theme: ThemeBundle,
) -> SettingsPanel:
    screen = SettingsPanel(
        parent,
        vehicle_configuration=vehicle_configuration,
        on_vehicle_configuration_changed=on_vehicle_configuration_changed,
        unit_system=unit_system,
        on_unit_system_changed=on_unit_system_changed,
        on_back=on_back,
        theme_bundle=theme,
    )
    screen.pack(fill=tk.BOTH, expand=True)
    return screen


def build_placeholder(parent: tk.Misc, name: str, *, theme: ThemeBundle) -> None:
    ui = theme.ui
    frame = panel(parent, name, ui.accent_success, theme=theme)
    frame.pack(fill=tk.BOTH, expand=True)
    tk.Label(
        frame,
        text=f"{name}\nCOMING NEXT",
        fg=ui.text,
        bg=ui.surface,
        font=("Sans", 24, "bold"),
    ).place(relx=0.5, rely=0.5, anchor="center")
