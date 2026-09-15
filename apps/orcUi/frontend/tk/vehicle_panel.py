# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full-screen vehicle telemetry panel for orcUi."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from .ecu_panel import EcuPanel
from .trip_panel import TripPanel
from .performance_panel import PerformancePanel
from .engine_panel import EnginePanel
from apps.orcUi.theme_runtime import theme_bundle as packaged_theme_bundle
from apps.orcUi.trip_presenter import TripPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from controllers.automotive import (
    AutomotiveTelemetryProfile,
    EngineAnalysis,
    EngineLoadLevel,
    EngineOperatingMode,
    FuelControlMode,
    FuelCorrectionStatus,
    MixtureMode,
    TrackingQuality,
    VehicleConfiguration,
)
from frontends.tk.automotive import OffroadDashboardPanel
from ui.navigation import HeadingReference, PositionFix
from ui.theme import ThemeBundle, ThemeMode


class VehiclePanel(tk.Frame):
    """ORC driving dashboard backed by reusable automotive instruments."""

    _TABS = ("PERFORMANCE", "HEALTH", "ECU", "OFF-ROAD", "TRIP")

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None],
        on_telemetry_profile: Callable[[AutomotiveTelemetryProfile], None] | None = None,
        state: VehiclePresentationState | None = None,
        trip_state: TripPresentationState | None = None,
        position: PositionPresentationState | None = None,
        attitude: AttitudePresentationState | None = None,
        theme_bundle: ThemeBundle | None = None,
        vehicle_configuration: VehicleConfiguration = VehicleConfiguration(),
        engine_analysis: EngineAnalysis | None = None,
    ) -> None:
        self._theme_bundle = theme_bundle or packaged_theme_bundle(ThemeMode.DARK)
        self._vehicle_configuration = vehicle_configuration
        self._engine_analysis = engine_analysis or EngineAnalysis(
            operating_mode=EngineOperatingMode.UNKNOWN,
            fuel_control_mode=FuelControlMode.UNKNOWN,
            mixture_mode=MixtureMode.UNKNOWN,
            mixture_tracking=TrackingQuality.UNKNOWN,
            throttle_tracking=TrackingQuality.UNKNOWN,
            fuel_correction_status=FuelCorrectionStatus.UNKNOWN,
            load_level=EngineLoadLevel.UNKNOWN,
            engine_running=None,
            warmed_up=None,
            enrichment_active=None,
            high_load=None,
            forced_induction_active=None,
            fuel_trim_total=None,
            mixture_tracking_error=None,
            throttle_tracking_error=None,
        )
        ui = self._theme_bundle.ui
        super().__init__(parent, bg=ui.background)
        self._on_back = on_back
        self._on_telemetry_profile = on_telemetry_profile
        self._state = state or VehiclePresentationState()
        self._trip_state = trip_state or TripPresentationState()
        self._position = position or PositionPresentationState()
        self._attitude = attitude or AttitudePresentationState()
        self._current_view = "PERFORMANCE"
        self._view_buttons: dict[str, tk.Button] = {}
        self._performance_panel: PerformancePanel | None = None
        self._engine_panel: EnginePanel | None = None
        self._offroad: OffroadDashboardPanel | None = None
        self._trip_panel: TripPanel | None = None
        self._ecu_panel: EcuPanel | None = None
        self._view_content: tk.Widget | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._tabs = tk.Frame(self, bg=ui.background)
        self._tabs.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        for column, name in enumerate(self._TABS):
            self._tabs.grid_columnconfigure(column, weight=1)
            button = tk.Button(
                self._tabs,
                text=name,
                command=lambda selected=name: self._show_view(selected),
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9, "bold"),
                pady=5,
            )
            button.grid(row=0, column=column, sticky="ew", padx=(0, 4))
            self._view_buttons[name] = button

        self._view_host = tk.Frame(self, bg=ui.background)
        self._view_host.grid(row=1, column=0, sticky="nsew")
        self._view_host.grid_columnconfigure(0, weight=1)
        self._view_host.grid_rowconfigure(0, weight=1)
        self._show_view(self._current_view)

    def _show_view(self, name: str) -> None:
        if name not in self._TABS:
            raise ValueError(f"Unknown vehicle view: {name}")
        self._current_view = name
        self._request_telemetry_profile(name)
        ui = self._theme_bundle.ui
        for view_name, button in self._view_buttons.items():
            active = view_name == name
            button.configure(
                bg=ui.control_active if active else ui.control_background,
                fg="#ffffff" if active else ui.text_muted,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                highlightbackground=ui.border,
            )
        if self._view_content is not None:
            self._view_content.destroy()
        self._view_content = None
        self._performance_panel = None
        self._engine_panel = None
        self._offroad = None
        self._trip_panel = None
        self._ecu_panel = None

        if name == "PERFORMANCE":
            self._show_performance()
        elif name == "HEALTH":
            self._show_engine()
        elif name == "ECU":
            self._show_ecu()
        elif name == "OFF-ROAD":
            self._show_offroad()
        else:
            self._show_trip()

    def release_telemetry_profile(self) -> None:
        if self._on_telemetry_profile is not None:
            self._on_telemetry_profile(AutomotiveTelemetryProfile.BACKGROUND)

    def _request_telemetry_profile(self, view_name: str) -> None:
        if self._on_telemetry_profile is None:
            return
        profile = {
            "PERFORMANCE": AutomotiveTelemetryProfile.PERFORMANCE,
            "HEALTH": AutomotiveTelemetryProfile.ENGINE,
            "ECU": AutomotiveTelemetryProfile.ECU,
            "TRIP": AutomotiveTelemetryProfile.TRIP,
            "OFF-ROAD": AutomotiveTelemetryProfile.BACKGROUND,
        }[view_name]
        self._on_telemetry_profile(profile)

    def _show_performance(self) -> None:
        panel = PerformancePanel(
            self._view_host,
            theme=self._theme_bundle,
            vehicle_configuration=self._vehicle_configuration,
            state=self._state,
            trip_state=self._trip_state,
        )
        panel.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self._performance_panel = panel
        self._view_content = panel

    def _show_engine(self) -> None:
        panel = EnginePanel(
            self._view_host,
            theme=self._theme_bundle,
            state=self._state,
        )
        panel.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self._engine_panel = panel
        self._view_content = panel

    def _show_ecu(self) -> None:
        panel = EcuPanel(
            self._view_host,
            theme=self._theme_bundle,
            vehicle_configuration=self._vehicle_configuration,
            vehicle_state=self._state,
            engine_analysis=self._engine_analysis,
        )
        panel.grid(row=0, column=0, sticky="nsew")
        self._ecu_panel = panel
        self._view_content = panel

    def update_engine_analysis(self, analysis: EngineAnalysis) -> None:
        self._engine_analysis = analysis
        if self._ecu_panel is not None:
            self._ecu_panel.update_analysis(analysis)

    def _show_offroad(self) -> None:
        panel = OffroadDashboardPanel(
            self._view_host,
            pitch_warning_deg=30.0,
            roll_warning_deg=25.0,
            request_handler=None,
        )
        panel.set_style_sheet(self._theme_bundle.style_sheet)
        panel.grid(row=0, column=0, sticky="nsew")
        self._offroad = panel
        self._view_content = panel
        self._apply_offroad_state()

    def _show_placeholder(self, title: str, detail: str) -> None:
        ui = self._theme_bundle.ui
        frame = tk.Frame(self._view_host, bg=ui.background)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        body = tk.Frame(
            frame,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        body.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        tk.Label(
            body,
            text=title,
            fg=ui.text,
            bg=ui.surface,
            font=("Sans", 22, "bold"),
        ).pack(pady=(80, 10))
        tk.Label(
            body,
            text=detail,
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", 11),
        ).pack()
        self._view_content = frame

    def _show_trip(self) -> None:
        panel = TripPanel(
            self._view_host,
            theme=self._theme_bundle,
            vehicle_configuration=self._vehicle_configuration,
            state=self._trip_state,
        )
        panel.grid(row=0, column=0, sticky="nsew")
        self._trip_panel = panel
        self._view_content = panel

    def show_trip_view(self) -> None:
        """Switch the vehicle panel directly to its trip view."""
        self._show_view("TRIP")

    def update_trip_state(self, state: TripPresentationState) -> None:
        self._trip_state = state
        if self._performance_panel is not None:
            self._performance_panel.update_trip(state)
        if self._trip_panel is not None:
            self._trip_panel.update_state(state)

    def set_vehicle_configuration(
        self,
        configuration: VehicleConfiguration,
    ) -> None:
        if configuration == self._vehicle_configuration:
            return
        self._vehicle_configuration = configuration
        self._show_view(self._current_view)

    def set_theme_bundle(self, theme_bundle: ThemeBundle) -> None:
        """Apply the active CSS theme and rebuild the active instrument view."""
        self._theme_bundle = theme_bundle
        theme = theme_bundle.ui
        self.configure(bg=theme.background)
        self._tabs.configure(bg=theme.background)
        self._view_host.configure(bg=theme.background)

        # Instrument widgets cache drawing colors and panel backgrounds. Rebuild
        # the active view from the new style sheet instead of translating old
        # widget colors or leaving a half-themed dashboard behind.
        self._show_view(self._current_view)

    def update_state(self, state: VehiclePresentationState) -> None:
        self._state = state
        self._apply_state()

    def update_position(self, state: PositionPresentationState) -> None:
        self._position = state
        self._apply_offroad_state()

    def update_attitude(self, state: AttitudePresentationState) -> None:
        self._attitude = state
        self._apply_offroad_state()

    def _apply_state(self) -> None:
        if self._performance_panel is not None:
            self._performance_panel.update_state(self._state)

        if self._engine_panel is not None:
            self._engine_panel.update_state(self._state)
        if self._ecu_panel is not None:
            self._ecu_panel.update_vehicle(self._state)

    def _apply_offroad_state(self) -> None:
        panel = self._offroad
        if panel is None:
            return
        attitude = self._attitude
        panel.set_heading(
            None if attitude.heading_deg is None else math.radians(attitude.heading_deg),
            HeadingReference.RELATIVE,
        )
        panel.set_pitch(None if attitude.pitch_deg is None else math.radians(attitude.pitch_deg))
        panel.set_roll(None if attitude.roll_deg is None else math.radians(attitude.roll_deg))
        position = self._position
        if position.latitude_deg is not None and position.longitude_deg is not None:
            altitude_m = (
                None
                if position.altitude_ft is None
                else position.altitude_ft / 3.280839895013123
            )
            panel.set_position(
                PositionFix(
                    latitude_rad=math.radians(position.latitude_deg),
                    longitude_rad=math.radians(position.longitude_deg),
                    altitude_m=altitude_m,
                    pfom_m=position.accuracy_m,
                )
            )
        else:
            panel.set_position(None)
