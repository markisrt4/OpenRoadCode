# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Built-in orcUi screen constructors."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from apps.orcUi.trip_presenter import TripPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from controllers.automotive import (
    AutomotiveTelemetryProfile,
    EngineAnalysis,
    VehicleConfiguration,
)
from ui.navigation import MapRequestHandlerIf
from ui.theme import ThemeBundle

from .navigation_panel import NavigationPanel
from .offroad_panel import OffRoadPanel
from .settings_panel import SettingsPanel
from .shell_content import panel
from .vehicle_panel import VehiclePanel


def build_navigation_screen(
    parent: tk.Misc,
    *,
    map_request_handler: MapRequestHandlerIf,
    on_back: Callable[[], None],
    theme: ThemeBundle,
) -> NavigationPanel:
    screen = NavigationPanel(
        parent,
        map_request_handler=map_request_handler,
        on_back=on_back,
        theme_bundle=theme,
    )
    screen.pack(fill=tk.BOTH, expand=True)
    return screen


def build_vehicle_screen(
    parent: tk.Misc,
    *,
    on_back: Callable[[], None],
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
    on_back: Callable[[], None],
    theme: ThemeBundle,
) -> SettingsPanel:
    screen = SettingsPanel(
        parent,
        vehicle_configuration=vehicle_configuration,
        on_vehicle_configuration_changed=on_vehicle_configuration_changed,
        on_back=on_back,
        theme_bundle=theme,
    )
    screen.pack(fill=tk.BOTH, expand=True)
    return screen


def build_offroad_screen(
    parent: tk.Misc,
    *,
    on_back: Callable[[], None],
    position: PositionPresentationState,
    attitude: AttitudePresentationState,
    theme: ThemeBundle,
) -> OffRoadPanel:
    screen = OffRoadPanel(
        parent,
        on_back=on_back,
        position=position,
        attitude=attitude,
        theme=theme.ui,
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
