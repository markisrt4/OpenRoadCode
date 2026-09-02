# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full-screen vehicle telemetry panel for orcUi."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable
from types import SimpleNamespace

from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from frontends.tk.automotive import DEFAULT_GAUGES, OffroadDashboardPanel, ShifterGauge, VehicleGaugePanel
from frontends.tk.automotive.vehicle_gauge_theme import (
    vehicle_gauge_theme_from_style_sheet,
)
from frontends.tk.automotive.vehicle_gauge_widgets import LinearGauge
from ui.navigation import HeadingReference, PositionFix
from ui.theme import ThemeBundle

BG = "#000000"
TAB_BG = "#101820"
TAB_ACTIVE = "#168bd1"
TEXT = "#edf2f5"
MUTED = "#89959e"


class VehiclePanel(tk.Frame):
    """ORC driving dashboard backed by reusable automotive instruments."""

    _TABS = ("PERFORMANCE", "ENGINE", "OFF-ROAD", "TRIP")
    _PERFORMANCE_IDS = ("rpm", "boost", "speed", "throttle")
    _ENGINE_IDS = ("coolant", "intake", "load", "fuel", "voltage")

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None],
        state: VehiclePresentationState | None = None,
        position: PositionPresentationState | None = None,
        attitude: AttitudePresentationState | None = None,
        theme_bundle: ThemeBundle | None = None,
    ) -> None:
        self._theme_bundle = theme_bundle
        background = theme_bundle.ui.background if theme_bundle is not None else BG
        super().__init__(parent, bg=background)
        self._on_back = on_back
        self._state = state or VehiclePresentationState()
        self._position = position or PositionPresentationState()
        self._attitude = attitude or AttitudePresentationState()
        self._current_view = "PERFORMANCE"
        self._view_buttons: dict[str, tk.Button] = {}
        self._gauges: VehicleGaugePanel | None = None
        self._engine_gauges: dict[str, LinearGauge] = {}
        self._shifter: ShifterGauge | None = None
        self._offroad: OffroadDashboardPanel | None = None
        self._view_content: tk.Widget | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        tabs = tk.Frame(self, bg=background)
        tabs.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        for column, name in enumerate(self._TABS):
            tabs.grid_columnconfigure(column, weight=1)
            ui_theme = theme_bundle.ui if theme_bundle is not None else None
            button = tk.Button(
                tabs,
                text=name,
                command=lambda selected=name: self._show_view(selected),
                bg=ui_theme.control_background if ui_theme is not None else TAB_BG,
                fg=ui_theme.control_text if ui_theme is not None else TEXT,
                activebackground=ui_theme.control_active if ui_theme is not None else TAB_ACTIVE,
                activeforeground=ui_theme.control_text if ui_theme is not None else TEXT,
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9, "bold"),
                pady=5,
            )
            button.grid(row=0, column=column, sticky="ew", padx=(0, 4))
            self._view_buttons[name] = button

        self._view_host = tk.Frame(self, bg=background)
        self._view_host.grid(row=1, column=0, sticky="nsew")
        self._view_host.grid_columnconfigure(0, weight=1)
        self._view_host.grid_rowconfigure(0, weight=1)
        self._show_view(self._current_view)

    def _show_view(self, name: str) -> None:
        if name not in self._TABS:
            raise ValueError(f"Unknown vehicle view: {name}")
        self._current_view = name
        ui_theme = self._theme_bundle.ui if self._theme_bundle is not None else None
        for view_name, button in self._view_buttons.items():
            active = view_name == name
            if ui_theme is None:
                button.configure(
                    bg=TAB_ACTIVE if active else TAB_BG,
                    fg=TEXT if active else MUTED,
                )
            else:
                button.configure(
                    bg=ui_theme.control_active if active else ui_theme.control_background,
                    fg=ui_theme.control_text if active else ui_theme.text_muted,
                    activebackground=ui_theme.control_active,
                    activeforeground=ui_theme.control_text,
                    highlightbackground=ui_theme.border,
                )
        if self._view_content is not None:
            self._view_content.destroy()
        self._view_content = None
        self._gauges = None
        self._engine_gauges.clear()
        self._shifter = None
        self._offroad = None

        if name == "PERFORMANCE":
            self._show_performance()
        elif name == "ENGINE":
            self._show_engine()
        elif name == "OFF-ROAD":
            self._show_offroad()
        else:
            self._show_placeholder("TRIP", "Trip distance, time, economy and drive statistics will live here.")

    def _show_performance(self) -> None:
        background = (
            self._theme_bundle.ui.background
            if self._theme_bundle is not None
            else BG
        )
        host = tk.Frame(self._view_host, bg=background)
        host.grid(row=0, column=0, sticky="nsew")
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(0, weight=1)

        definitions = tuple(definition for definition in DEFAULT_GAUGES if definition.gauge_id in self._PERFORMANCE_IDS)
        panel = VehicleGaugePanel(
            host,
            definitions=definitions,
            columns=4,
            show_config_button=False,
            panel_background=background,
        )
        if self._theme_bundle is not None:
            panel.set_style_sheet(self._theme_bundle.style_sheet)
        panel.grid(row=0, column=0, sticky="nsew")
        panel._toolbar.grid_remove()  # type: ignore[attr-defined]

        shifter = ShifterGauge(host, width=280, height=58)
        if self._theme_bundle is not None:
            shifter.set_style_sheet(self._theme_bundle.style_sheet)
        shifter.grid(row=1, column=0, pady=(0, 3))

        self._gauges = panel
        self._shifter = shifter
        self._view_content = host
        self._apply_state()

    def _show_engine(self) -> None:
        """Show compact secondary gauges two across."""
        background = (
            self._theme_bundle.ui.background
            if self._theme_bundle is not None
            else BG
        )
        host = tk.Frame(self._view_host, bg=background)
        host.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        host.grid_columnconfigure(0, weight=1, uniform="engine")
        host.grid_columnconfigure(1, weight=1, uniform="engine")
        for row in range(3):
            host.grid_rowconfigure(row, weight=1)

        definitions = {definition.gauge_id: definition for definition in DEFAULT_GAUGES if definition.gauge_id in self._ENGINE_IDS}
        gauge_style = (
            vehicle_gauge_theme_from_style_sheet(self._theme_bundle.style_sheet)
            if self._theme_bundle is not None
            else None
        )
        for index, gauge_id in enumerate(self._ENGINE_IDS):
            definition = definitions[gauge_id]
            gauge = LinearGauge(
                host,
                title=definition.title,
                unit=definition.unit,
                minimum=definition.minimum,
                maximum=definition.maximum,
                caution_low=definition.caution_low,
                danger_low=definition.danger_low,
                caution_high=definition.caution_high,
                danger_high=definition.danger_high,
                icon=definition.icon,
                precision=definition.precision,
                style=gauge_style,
                width=260,
                height=95,
            )
            row, column = divmod(index, 2)
            gauge.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)
            self._engine_gauges[gauge_id] = gauge

        self._view_content = host
        self._apply_state()

    def _show_offroad(self) -> None:
        """Embed the original reusable off-road dashboard."""
        panel = OffroadDashboardPanel(
            self._view_host,
            pitch_warning_deg=30.0,
            roll_warning_deg=25.0,
            request_handler=None,
        )
        panel.grid(row=0, column=0, sticky="nsew")
        self._offroad = panel
        self._view_content = panel
        self._apply_offroad_state()

    def _show_placeholder(self, title: str, detail: str) -> None:
        frame = tk.Frame(self._view_host, bg=BG)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        body = tk.Frame(frame, bg="#0b1117", highlightthickness=1, highlightbackground="#25313b")
        body.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        tk.Label(body, text=title, fg=TEXT, bg="#0b1117", font=("Sans", 22, "bold")).pack(pady=(80, 10))
        tk.Label(body, text=detail, fg=MUTED, bg="#0b1117", font=("Sans", 11)).pack()
        self._view_content = frame

    def set_theme_bundle(self, theme_bundle: ThemeBundle) -> None:
        """Apply the active application theme to ORC-owned vehicle controls."""

        self._theme_bundle = theme_bundle
        theme = theme_bundle.ui
        self.configure(bg=theme.background)
        self._view_host.configure(bg=theme.background)

        for view_name, button in self._view_buttons.items():
            active = view_name == self._current_view
            button.configure(
                bg=theme.control_active if active else theme.control_background,
                fg=theme.control_text if active else theme.text_muted,
                activebackground=theme.control_active,
                activeforeground=theme.control_text,
                highlightbackground=theme.border,
            )

        if self._shifter is not None:
            self._shifter.set_style_sheet(theme_bundle.style_sheet)

        if self._gauges is not None:
            self._gauges.set_style_sheet(theme_bundle.style_sheet)

        if self._engine_gauges:
            # Recreate direct gauge widgets so every Canvas redraw uses the
            # newly resolved component theme.
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
        gauge_state = SimpleNamespace(
            rpm=self._state.engine_speed_rpm,
            speed_mph=self._state.speed_mph,
            boost_psi=self._state.boost_psi,
            throttle_pct=self._state.throttle_percent,
            coolant_temp_f=self._state.coolant_temperature_f,
            intake_temp_f=self._state.intake_air_temperature_f,
            engine_load_pct=self._state.engine_load_percent,
            control_voltage=self._state.control_voltage_v,
            fuel_level_pct=self._state.fuel_percent,
        )
        if self._gauges is not None:
            self._gauges.update_state(gauge_state, connected=True)
        if self._shifter is not None:
            self._shifter.set_gear(self._state.gear)

        engine_values = {
            "coolant": self._state.coolant_temperature_f,
            "intake": self._state.intake_air_temperature_f,
            "load": self._state.engine_load_percent,
            "fuel": self._state.fuel_percent,
            "voltage": self._state.control_voltage_v,
        }
        for gauge_id, gauge in self._engine_gauges.items():
            gauge.set_connected(True)
            gauge.set_value(engine_values[gauge_id])

    def _apply_offroad_state(self) -> None:
        panel = self._offroad
        if panel is None:
            return
        attitude = self._attitude
        panel.set_heading(None if attitude.heading_deg is None else math.radians(attitude.heading_deg), HeadingReference.RELATIVE)
        panel.set_pitch(None if attitude.pitch_deg is None else math.radians(attitude.pitch_deg))
        panel.set_roll(None if attitude.roll_deg is None else math.radians(attitude.roll_deg))
        position = self._position
        if position.latitude_deg is not None and position.longitude_deg is not None:
            altitude_m = None if position.altitude_ft is None else position.altitude_ft / 3.280839895013123
            panel.set_position(PositionFix(latitude_rad=math.radians(position.latitude_deg), longitude_rad=math.radians(position.longitude_deg), altitude_m=altitude_m, pfom_m=position.accuracy_m))
        else:
            panel.set_position(None)
        panel.set_status("Navigation online")
