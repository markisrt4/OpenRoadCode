# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full-screen vehicle telemetry panel for orcUi."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
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
from frontends.tk.automotive import DEFAULT_GAUGES, OffroadDashboardPanel, ShifterGauge
from frontends.tk.automotive.vehicle_gauge_theme import vehicle_gauge_theme_from_style_sheet
from frontends.tk.automotive.vehicle_gauge_widgets import LinearGauge, RoundGauge
from frontends.tk.automotive.trip_metric_card import TripMetricCard
from ui.navigation import HeadingReference, PositionFix
from ui.theme import ThemeBundle, ThemeMode


class VehiclePanel(tk.Frame):
    """ORC driving dashboard backed by reusable automotive instruments."""

    _TABS = ("PERFORMANCE", "ENGINE", "ECU", "OFF-ROAD", "TRIP")
    _PERFORMANCE_IDS = ("rpm", "boost", "speed", "throttle")
    _ENGINE_IDS = ("coolant", "intake", "load", "fuel", "voltage")

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
        self._gauges: dict[str, RoundGauge] = {}
        self._engine_gauges: dict[str, LinearGauge] = {}
        self._shifter: ShifterGauge | None = None
        self._offroad: OffroadDashboardPanel | None = None
        self._trip_cards: dict[str, TripMetricCard] = {}
        self._boost_metric_labels: dict[str, tk.Label] = {}
        self._ecu_value_labels: dict[str, tk.Label] = {}
        self._ecu_state_labels: dict[str, tk.Label] = {}
        self._ecu_canvases: dict[str, tk.Canvas] = {}
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
        self._gauges.clear()
        self._engine_gauges.clear()
        self._shifter = None
        self._offroad = None
        self._trip_cards.clear()
        self._boost_metric_labels.clear()
        self._ecu_value_labels.clear()
        self._ecu_state_labels.clear()
        self._ecu_canvases.clear()

        if name == "PERFORMANCE":
            self._show_performance()
        elif name == "ENGINE":
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
            "ENGINE": AutomotiveTelemetryProfile.ENGINE,
            "ECU": AutomotiveTelemetryProfile.ECU,
            "TRIP": AutomotiveTelemetryProfile.TRIP,
            "OFF-ROAD": AutomotiveTelemetryProfile.BACKGROUND,
        }[view_name]
        self._on_telemetry_profile(profile)

    def _show_performance(self) -> None:
        ui = self._theme_bundle.ui
        background = ui.background
        host = tk.Frame(self._view_host, bg=background)
        host.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(1, weight=1)

        header = self._section_header(
            host,
            title="PERFORMANCE",
            subtitle="Live driving dynamics",
            accent=ui.accent_danger,
            symbol="◉",
        )
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        cluster = tk.Frame(host, bg=background)
        cluster.grid(row=1, column=0, sticky="nsew")
        cluster.grid_rowconfigure(0, weight=1)
        for column in range(4):
            cluster.grid_columnconfigure(column, weight=1, uniform="performance")

        definitions = {
            definition.gauge_id: definition
            for definition in DEFAULT_GAUGES
            if definition.gauge_id in self._PERFORMANCE_IDS
        }
        gauge_style = vehicle_gauge_theme_from_style_sheet(self._theme_bundle.style_sheet)

        for column, gauge_id in enumerate(self._PERFORMANCE_IDS):
            definition = definitions[gauge_id]
            title = definition.title.upper()
            if gauge_id == "boost" and not self._vehicle_configuration.induction.is_forced_induction:
                title = "MANIFOLD"
            card = self._instrument_card(
                cluster,
                title=title,
                unit=definition.unit,
            )
            card.grid(row=0, column=column, sticky="nsew", padx=4, pady=2)
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)

            gauge = RoundGauge(
                card,
                title="",
                unit=definition.unit,
                minimum=definition.minimum,
                maximum=definition.maximum,
                major_step=definition.major_step,
                caution_start=definition.caution_high,
                danger_start=definition.danger_high,
                intense_redline=definition.intense_redline,
                redline_style=definition.redline_style,
                start_angle=definition.start_angle,
                sweep_angle=definition.sweep_angle,
                precision=definition.precision,
                style=gauge_style,
                size=205,
            )
            gauge.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0, 2))
            self._gauges[gauge_id] = gauge

        lower = tk.Frame(host, bg=background)
        lower.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        lower.grid_columnconfigure(0, weight=1)

        shifter = ShifterGauge(lower, width=280, height=58)
        shifter.set_style_sheet(self._theme_bundle.style_sheet)
        shifter.grid(row=0, column=0)
        self._shifter = shifter

        self._view_content = host
        self._apply_state()

    def _show_engine(self) -> None:
        ui = self._theme_bundle.ui
        background = ui.background
        host = tk.Frame(self._view_host, bg=background)
        host.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(1, weight=1)

        header = self._section_header(
            host,
            title="ENGINE",
            subtitle="Powertrain health and operating conditions",
            accent=ui.accent_warning,
            symbol="⌁",
        )
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        grid = tk.Frame(host, bg=background)
        grid.grid(row=1, column=0, sticky="nsew")
        grid.grid_columnconfigure(0, weight=1, uniform="engine")
        grid.grid_columnconfigure(1, weight=1, uniform="engine")
        for row in range(3):
            grid.grid_rowconfigure(row, weight=1)

        definitions = {
            definition.gauge_id: definition
            for definition in DEFAULT_GAUGES
            if definition.gauge_id in self._ENGINE_IDS
        }
        gauge_style = vehicle_gauge_theme_from_style_sheet(self._theme_bundle.style_sheet)

        for index, gauge_id in enumerate(self._ENGINE_IDS):
            definition = definitions[gauge_id]
            row, column = divmod(index, 2)
            card = self._instrument_card(
                grid,
                title=definition.title.upper(),
                unit=definition.unit,
            )
            card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)

            gauge = LinearGauge(
                card,
                title="",
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
                height=82,
            )
            gauge.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
            self._engine_gauges[gauge_id] = gauge

        summary = tk.Frame(
            grid,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        summary.grid(row=2, column=1, sticky="nsew", padx=4, pady=4)
        tk.Label(
            summary,
            text="ENGINE STATUS",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", 8, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 4))
        tk.Label(
            summary,
            text="Monitoring live sensors",
            fg=ui.text,
            bg=ui.surface_alt,
            font=("Sans", 12, "bold"),
        ).pack(anchor="w", padx=12)
        tk.Label(
            summary,
            text="Coolant · Intake · Load · Fuel · Voltage",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", 8),
        ).pack(anchor="w", padx=12, pady=(4, 10))

        self._view_content = host
        self._apply_state()

    def _section_header(
        self,
        parent: tk.Misc,
        *,
        title: str,
        subtitle: str,
        accent: str,
        symbol: str,
    ) -> tk.Frame:
        ui = self._theme_bundle.ui
        header = tk.Frame(
            parent,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        marker = tk.Frame(header, bg=accent, width=5)
        marker.pack(side=tk.LEFT, fill=tk.Y)

        icon = tk.Label(
            header,
            text=symbol,
            fg=accent,
            bg=ui.surface_alt,
            font=("Sans", 22, "bold"),
            width=3,
        )
        icon.pack(side=tk.LEFT, padx=(10, 4), pady=8)

        text = tk.Frame(header, bg=ui.surface_alt)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=7)
        tk.Label(
            text,
            text=title,
            fg=ui.text,
            bg=ui.surface_alt,
            font=("Sans", 16, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            text,
            text=subtitle,
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", 8),
            anchor="w",
        ).pack(anchor="w")
        return header

    def _instrument_card(
        self,
        parent: tk.Misc,
        *,
        title: str,
        unit: str,
    ) -> tk.Frame:
        ui = self._theme_bundle.ui
        card = tk.Frame(
            parent,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        top = tk.Frame(card, bg=ui.surface)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(7, 2))
        top.grid_columnconfigure(1, weight=1)
        tk.Label(
            top,
            text=title,
            fg=ui.text,
            bg=ui.surface,
            font=("Sans", 11, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        if unit:
            tk.Label(
                top,
                text=unit,
                fg=ui.text_muted,
                bg=ui.surface,
                font=("Sans", 9, "bold"),
            ).grid(row=0, column=1, sticky="e")
        return card


    def _show_ecu(self) -> None:
        ui = self._theme_bundle.ui
        host = tk.Frame(self._view_host, bg=ui.background)
        host.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(1, weight=1)
        self._section_header(
            host,
            title="ECU MONITOR",
            subtitle="What the engine computer is doing right now",
            accent=ui.accent_primary,
            symbol="◆",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        grid = tk.Frame(host, bg=ui.background)
        grid.grid(row=1, column=0, sticky="nsew")
        grid.grid_rowconfigure(0, weight=1)
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="ecu")

        cards = (
            ("FUEL CONTROL", ui.accent_warning, "fuel"),
            ("MIXTURE", ui.accent_primary, "mixture"),
            ("ENGINE LOAD", ui.accent_danger, "load"),
        )
        for column, (title, accent, key) in enumerate(cards):
            card = tk.Frame(
                grid,
                bg=ui.surface,
                highlightthickness=1,
                highlightbackground=ui.border,
            )
            card.grid(row=0, column=column, sticky="nsew", padx=4, pady=4)
            card.grid_columnconfigure(0, weight=1)
            tk.Frame(card, bg=accent, height=4).grid(row=0, column=0, sticky="ew")
            tk.Label(
                card,
                text=title,
                fg=accent,
                bg=ui.surface,
                font=("Sans", 10, "bold"),
            ).grid(row=1, column=0, sticky="w", padx=14, pady=(10, 4))

            primary = tk.Label(
                card,
                text="--",
                fg=ui.text,
                bg=ui.surface,
                font=("Sans", 20, "bold"),
                anchor="w",
            )
            primary.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 0))
            secondary = tk.Label(
                card,
                text="--",
                fg=ui.text_muted,
                bg=ui.surface,
                font=("Sans", 12, "bold"),
                anchor="w",
            )
            secondary.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))
            detail = tk.Label(
                card,
                text="",
                fg=ui.text_muted,
                bg=ui.surface,
                font=("Sans", 11),
                justify=tk.LEFT,
                anchor="w",
            )
            detail.grid(row=4, column=0, sticky="sw", padx=14, pady=(4, 8))
            visual = tk.Canvas(
                card,
                height=88,
                bg=ui.surface,
                highlightthickness=0,
                bd=0,
            )
            visual.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 10))
            self._ecu_canvases[key] = visual
            self._ecu_value_labels[f"{key}_primary"] = primary
            self._ecu_value_labels[f"{key}_secondary"] = secondary
            self._ecu_value_labels[f"{key}_detail"] = detail

        state_card = tk.Frame(
            host,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        state_card.grid(row=2, column=0, sticky="ew", padx=4, pady=(4, 2))
        state_card.grid_columnconfigure(1, weight=1)

        tk.Label(
            state_card,
            text="ENGINE STATE",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", 9, "bold"),
        ).grid(row=0, column=0, rowspan=2, sticky="w", padx=(14, 18), pady=10)

        mode = tk.Label(
            state_card,
            text="--",
            fg=ui.accent_primary,
            bg=ui.surface_alt,
            font=("Sans", 15, "bold"),
            width=14,
            anchor="w",
        )
        mode.grid(row=0, column=1, sticky="w", pady=(8, 0))
        self._ecu_value_labels["operating_mode"] = mode

        condition_host = tk.Frame(state_card, bg=ui.surface_alt)
        condition_host.grid(row=1, column=1, sticky="w", pady=(0, 8))
        conditions = ["HIGH LOAD", "ENRICHMENT", "WARM-UP"]
        if self._vehicle_configuration.induction.is_forced_induction:
            conditions.insert(1, "BOOST")
        for name in conditions:
            label = tk.Label(
                condition_host,
                text="○ " + name,
                fg=ui.text_muted,
                bg=ui.surface_alt,
                font=("Sans", 9, "bold"),
                width=14,
                anchor="w",
            )
            label.pack(side=tk.LEFT, padx=2)
            self._ecu_state_labels[name] = label

        self._view_content = host
        self._apply_ecu_state()

    def _apply_ecu_state(self) -> None:
        if not self._ecu_value_labels:
            return

        ui = self._theme_bundle.ui
        state = self._state
        analysis = self._engine_analysis

        fuel_mode = {
            FuelControlMode.OPEN_LOOP_WARMUP: "OPEN LOOP",
            FuelControlMode.CLOSED_LOOP: "CLOSED LOOP",
            FuelControlMode.OPEN_LOOP_LOAD_OR_DECEL: "OPEN LOOP",
            FuelControlMode.OPEN_LOOP_FAULT: "FAULT",
            FuelControlMode.CLOSED_LOOP_FAULT: "FAULT",
            FuelControlMode.UNKNOWN: "--",
        }[analysis.fuel_control_mode]
        correction = {
            FuelCorrectionStatus.NORMAL: "NORMAL",
            FuelCorrectionStatus.ADDING_FUEL: "ADDING FUEL",
            FuelCorrectionStatus.REMOVING_FUEL: "REMOVING FUEL",
            FuelCorrectionStatus.UNKNOWN: "--",
        }[analysis.fuel_correction_status]
        mixture = {
            MixtureMode.RICH: "RICH",
            MixtureMode.STOICHIOMETRIC: "STOICHIOMETRIC",
            MixtureMode.LEAN: "LEAN",
            MixtureMode.UNKNOWN: "--",
        }[analysis.mixture_mode]
        tracking = {
            TrackingQuality.GOOD: "TRACKING GOOD",
            TrackingQuality.MODERATE: "TRACKING FAIR",
            TrackingQuality.POOR: "TRACKING POOR",
            TrackingQuality.UNKNOWN: "--",
        }[analysis.mixture_tracking]
        load = {
            EngineLoadLevel.LOW: "LOW",
            EngineLoadLevel.MODERATE: "MODERATE",
            EngineLoadLevel.HIGH: "HIGH",
            EngineLoadLevel.UNKNOWN: "--",
        }[analysis.load_level]

        trim = (
            "--"
            if analysis.fuel_trim_total is None
            else f"Fuel correction {analysis.fuel_trim_total * 100.0:+.1f}%"
        )
        trims = (
            f"ST {state.short_term_fuel_trim_percent:+.1f}%  ·  "
            f"LT {state.long_term_fuel_trim_percent:+.1f}%"
            if state.short_term_fuel_trim_percent is not None
            and state.long_term_fuel_trim_percent is not None
            else ""
        )
        lambda_detail = (
            f"Target {state.commanded_equivalence_ratio:.3f}  ·  "
            f"Actual {state.measured_equivalence_ratio:.3f}"
            if state.commanded_equivalence_ratio is not None
            and state.measured_equivalence_ratio is not None
            else ""
        )
        load_detail = (
            f"{state.absolute_engine_load_percent:.0f}% absolute load"
            if state.absolute_engine_load_percent is not None
            else ""
        )
        if analysis.forced_induction_active is True:
            load_detail += "  ·  BOOST ACTIVE"

        values = {
            "fuel_primary": fuel_mode,
            "fuel_secondary": correction,
            "fuel_detail": trim + (("\n" + trims) if trims else ""),
            "mixture_primary": mixture,
            "mixture_secondary": tracking,
            "mixture_detail": lambda_detail,
            "load_primary": load,
            "load_secondary": (
                "BOOST ACTIVE"
                if analysis.forced_induction_active is True
                else "ENGINE DEMAND"
            ),
            "load_detail": load_detail,
            "operating_mode": analysis.operating_mode.value.replace("_", " ").upper(),
        }
        for key, text in values.items():
            label = self._ecu_value_labels.get(key)
            if label is not None:
                label.configure(text=text)

        fuel_color = ui.text
        if analysis.fuel_control_mode in {
            FuelControlMode.OPEN_LOOP_FAULT,
            FuelControlMode.CLOSED_LOOP_FAULT,
        }:
            fuel_color = ui.accent_danger
        elif analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP:
            fuel_color = ui.accent_success
        self._ecu_value_labels["fuel_primary"].configure(fg=fuel_color)

        tracking_color = {
            TrackingQuality.GOOD: ui.accent_success,
            TrackingQuality.MODERATE: ui.accent_warning,
            TrackingQuality.POOR: ui.accent_danger,
        }.get(analysis.mixture_tracking, ui.text_muted)
        self._ecu_value_labels["mixture_secondary"].configure(fg=tracking_color)

        self._draw_ecu_visuals()

        active = {
            "HIGH LOAD": analysis.high_load is True,
            "BOOST": analysis.forced_induction_active is True,
            "ENRICHMENT": analysis.enrichment_active is True,
            "WARM-UP": analysis.warmed_up is False,
        }
        for name, label in self._ecu_state_labels.items():
            enabled = active[name]
            label.configure(
                fg=ui.accent_success if enabled else ui.text_muted,
                text=("● " if enabled else "○ ") + name,
            )

    def _draw_ecu_visuals(self) -> None:
        ui = self._theme_bundle.ui
        state = self._state
        analysis = self._engine_analysis

        for canvas in self._ecu_canvases.values():
            canvas.delete("all")
            canvas.update_idletasks()

        def draw_segmented_bar(
            canvas: tk.Canvas,
            *,
            y: float,
            x1: float,
            x2: float,
            active_fraction: float | None,
            active_color: str,
            segments: int = 18,
        ) -> None:
            gap = 3
            usable = x2 - x1
            segment_width = (usable - gap * (segments - 1)) / segments
            for index in range(segments):
                sx1 = x1 + index * (segment_width + gap)
                sx2 = sx1 + segment_width
                active = (
                    active_fraction is not None
                    and (index + 1) / segments <= active_fraction + 1 / segments
                )
                canvas.create_rectangle(
                    sx1,
                    y - 6,
                    sx2,
                    y + 6,
                    fill=active_color if active else ui.surface_alt,
                    outline=ui.border,
                )

        fuel = self._ecu_canvases.get("fuel")
        if fuel is not None:
            width = max(220, fuel.winfo_width())
            x1, x2, y = 16, width - 16, 44
            fuel.create_text(
                x1, 11, anchor="w", text="REMOVE",
                fill=ui.text_muted, font=("Sans", 8, "bold"),
            )
            fuel.create_text(
                width / 2, 11, text="NORMAL",
                fill=ui.text_muted, font=("Sans", 8, "bold"),
            )
            fuel.create_text(
                x2, 11, anchor="e", text="ADD",
                fill=ui.text_muted, font=("Sans", 8, "bold"),
            )
            fuel.create_line(x1, y, x2, y, fill=ui.border, width=3)
            center = width / 2
            fuel.create_line(center, 27, center, 61, fill=ui.text, width=2)
            for pct, label in ((-20, "-20"), (0, "0"), (20, "+20%")):
                x = x1 + ((pct + 20) / 40) * (x2 - x1)
                fuel.create_line(x, y - 5, x, y + 5, fill=ui.text_muted)
                fuel.create_text(
                    x, 75, text=label, fill=ui.text_muted, font=("Sans", 8),
                )
            if analysis.fuel_trim_total is not None:
                trim_pct = max(-20.0, min(20.0, analysis.fuel_trim_total * 100.0))
                x = x1 + ((trim_pct + 20.0) / 40.0) * (x2 - x1)
                fuel.create_polygon(
                    x, y - 13,
                    x - 7, y - 24,
                    x + 7, y - 24,
                    fill=ui.accent_warning,
                    outline="",
                )
                fuel.create_oval(
                    x - 6, y - 6, x + 6, y + 6,
                    fill=ui.accent_warning, outline="",
                )

        mixture = self._ecu_canvases.get("mixture")
        if mixture is not None:
            width = max(220, mixture.winfo_width())
            x1, x2, y = 16, width - 16, 44
            mixture.create_text(
                x1, 11, anchor="w", text="RICH",
                fill=ui.accent_warning, font=("Sans", 8, "bold"),
            )
            mixture.create_text(
                width / 2, 11, text="STOICH",
                fill=ui.text, font=("Sans", 8, "bold"),
            )
            mixture.create_text(
                x2, 11, anchor="e", text="LEAN",
                fill=ui.accent_primary, font=("Sans", 8, "bold"),
            )
            mixture.create_line(x1, y, x2, y, fill=ui.border, width=4)
            stoich_x = x1 + ((1.0 - 0.70) / 0.60) * (x2 - x1)
            mixture.create_line(stoich_x, 24, stoich_x, 64, fill=ui.text, width=2)
            mixture.create_text(
                stoich_x, 75, text="1.00",
                fill=ui.text_muted, font=("Sans", 8, "bold"),
            )
            markers = (
                ("T", state.commanded_equivalence_ratio, ui.accent_primary, -13),
                ("A", state.measured_equivalence_ratio, ui.accent_success, 13),
            )
            for label, value, color, offset in markers:
                if value is None:
                    continue
                clamped = max(0.70, min(1.30, value))
                x = x1 + ((clamped - 0.70) / 0.60) * (x2 - x1)
                mixture.create_line(x, y + offset, x, y, fill=color, width=3)
                mixture.create_oval(
                    x - 6, y - 6, x + 6, y + 6,
                    fill=color, outline="",
                )
                mixture.create_text(
                    x, y + offset * 1.9, text=label,
                    fill=color, font=("Sans", 8, "bold"),
                )

        load = self._ecu_canvases.get("load")
        if load is not None:
            width = max(220, load.winfo_width())
            x1, x2 = 16, width - 16
            load.create_text(
                x1, 10, anchor="w", text="ENGINE LOAD",
                fill=ui.text_muted, font=("Sans", 8, "bold"),
            )
            load_fraction = (
                None
                if state.absolute_engine_load_percent is None
                else max(0.0, min(1.0, state.absolute_engine_load_percent / 150.0))
            )
            draw_segmented_bar(
                load,
                y=29,
                x1=x1,
                x2=x2,
                active_fraction=load_fraction,
                active_color=ui.accent_danger,
            )
            for fraction, label in ((0.0, "0"), (0.5, "75"), (1.0, "150%")):
                load.create_text(
                    x1 + fraction * (x2 - x1),
                    48,
                    anchor="w" if fraction == 0.0 else "e" if fraction == 1.0 else "center",
                    text=label,
                    fill=ui.text_muted,
                    font=("Sans", 8),
                )

            if self._vehicle_configuration.induction.is_forced_induction:
                load.create_text(
                    x1, 63, anchor="w", text="BOOST",
                    fill=ui.text_muted, font=("Sans", 8, "bold"),
                )
                boost = state.boost_psi
                boost_fraction = (
                    None
                    if boost is None
                    else max(0.0, min(1.0, boost / 20.0))
                )
                draw_segmented_bar(
                    load,
                    y=76,
                    x1=x1 + 54,
                    x2=x2,
                    active_fraction=boost_fraction,
                    active_color=ui.accent_primary,
                    segments=12,
                )
                load.create_text(
                    x2,
                    63,
                    anchor="e",
                    text="-- psi" if boost is None else f"{boost:+.1f} psi",
                    fill=ui.text,
                    font=("Sans", 8, "bold"),
                )

    def update_engine_analysis(self, analysis: EngineAnalysis) -> None:
        self._engine_analysis = analysis
        self._apply_ecu_state()

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
        ui = self._theme_bundle.ui
        host = tk.Frame(self._view_host, bg=ui.background)
        host.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        host.grid_columnconfigure(0, weight=1)
        host.grid_rowconfigure(1, weight=1)
        host.grid_rowconfigure(2, weight=0)

        header = tk.Frame(
            host,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        header.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 6))
        header.grid_columnconfigure(1, weight=1)

        road = tk.Canvas(
            header,
            width=70,
            height=58,
            bg=ui.surface_alt,
            highlightthickness=0,
            bd=0,
        )
        road.grid(row=0, column=0, rowspan=2, padx=(16, 10), pady=7)
        road.create_polygon(10, 54, 28, 7, 42, 7, 60, 54, fill=ui.accent_primary, outline="")
        road.create_line(35, 49, 35, 37, fill=ui.surface_alt, width=4)
        road.create_line(35, 30, 35, 21, fill=ui.surface_alt, width=3)
        road.create_line(35, 15, 35, 11, fill=ui.surface_alt, width=2)

        tk.Label(
            header,
            text="TRIP COMPUTER",
            fg=ui.text,
            bg=ui.surface_alt,
            font=("Sans", 18, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(8, 0))
        tk.Label(
            header,
            text="Track your journey. Know your drive.",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", 9),
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", pady=(0, 8))

        grid = tk.Frame(host, bg=ui.background)
        grid.grid(row=1, column=0, sticky="nsew")
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="trip")
        for row in range(3):
            grid.grid_rowconfigure(row, weight=1, uniform="trip")

        metrics = (
            ("status", "TRIP STATUS", "", "status", ui.accent_success),
            ("distance", "DISTANCE", "mi", "pin", ui.accent_primary),
            ("elapsed", "ELAPSED TIME", "", "clock", ui.accent_primary),
            ("moving", "MOVING TIME", "", "wheel", ui.accent_success),
            ("stopped", "STOPPED TIME", "", "pause", ui.accent_danger),
            ("average", "AVERAGE SPEED", "MPH", "speed", ui.accent_warning),
            ("maximum", "MAXIMUM SPEED", "MPH", "speed", ui.accent_warning),
            ("fuel_used", "FUEL USED", "gal", "fuel", ui.text_muted),
            ("economy", "FUEL ECONOMY", "MPG", "chart", ui.text_muted),
        )

        for index, (key, title, unit, icon, accent) in enumerate(metrics):
            row, column = divmod(index, 3)
            card = TripMetricCard(
                grid,
                title=title,
                unit=unit,
                icon=icon,
                background=ui.surface,
                border=ui.border,
                text=ui.text,
                muted=ui.text_muted,
                accent=accent,
            )
            card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
            self._trip_cards[key] = card

        if self._vehicle_configuration.induction.is_forced_induction:
            boost_band = tk.Frame(
                host,
                bg=ui.surface_alt,
                highlightthickness=1,
                highlightbackground=ui.border,
            )
            boost_band.grid(row=2, column=0, sticky="ew", padx=4, pady=(6, 2))
            tk.Label(
                boost_band,
                text="BOOST METRICS",
                fg=ui.text_muted,
                bg=ui.surface_alt,
                font=("Sans", 8, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=(12, 8), pady=9)

            boost_specs = (
                ("boost_time", "TIME", ""),
                ("boost_distance", "DIST", "mi"),
                ("boost_fuel", "FUEL", "gal"),
                ("boost_share", "FUEL SHARE", "%"),
                ("peak_boost", "PEAK", "psi"),
            )
            for column, (key, title, unit) in enumerate(boost_specs, start=1):
                cell = tk.Frame(boost_band, bg=ui.surface_alt)
                cell.grid(row=0, column=column, sticky="ew", padx=8, pady=5)
                boost_band.grid_columnconfigure(column, weight=1)
                tk.Label(
                    cell,
                    text=title,
                    fg=ui.text_muted,
                    bg=ui.surface_alt,
                    font=("Sans", 7, "bold"),
                ).pack()
                value = tk.Label(
                    cell,
                    text="--",
                    fg=ui.text,
                    bg=ui.surface_alt,
                    font=("Sans", 11, "bold"),
                )
                value.pack()
                if unit:
                    tk.Label(
                        cell,
                        text=unit,
                        fg=ui.text_muted,
                        bg=ui.surface_alt,
                        font=("Sans", 7),
                    ).pack()
                self._boost_metric_labels[key] = value

        self._view_content = host
        self._apply_trip_state()

    def show_trip_view(self) -> None:
        """Switch the vehicle panel directly to its trip view."""
        self._show_view("TRIP")

    def update_trip_state(self, state: TripPresentationState) -> None:
        self._trip_state = state
        self._apply_trip_state()

    def _apply_trip_state(self) -> None:
        if not self._trip_cards:
            return
        state = self._trip_state
        values = {
            "distance": f"{state.distance_miles:.1f}",
            "elapsed": self._format_duration(state.elapsed_s),
            "moving": self._format_duration(state.moving_s),
            "stopped": self._format_duration(state.stopped_s),
            "average": "--" if state.average_speed_mph is None else f"{state.average_speed_mph:.1f}",
            "maximum": "--" if state.maximum_speed_mph is None else f"{state.maximum_speed_mph:.1f}",
            "fuel_used": "--" if state.fuel_used_gallons is None else f"{state.fuel_used_gallons:.2f}",
            "economy": "--" if state.economy_mpg is None else f"{state.economy_mpg:.1f}",
            "status": state.status.upper(),
        }
        boost_values = {
            "boost_time": self._format_duration(state.boost_time_s),
            "boost_distance": f"{state.boost_distance_miles:.1f}",
            "boost_fuel": f"{state.boost_fuel_gallons:.2f}",
            "boost_share": "--" if state.boost_fuel_percent is None else f"{state.boost_fuel_percent:.0f}",
            "peak_boost": "--" if state.peak_boost_psi is None else f"{state.peak_boost_psi:.1f}",
        }
        for key, text in boost_values.items():
            label = self._boost_metric_labels.get(key)
            if label is not None:
                label.configure(text=text)

        status_colors = {
            "active": self._theme_bundle.ui.accent_success,
            "paused": self._theme_bundle.ui.accent_warning,
            "complete": self._theme_bundle.ui.accent_primary,
            "idle": self._theme_bundle.ui.text_muted,
        }
        for key, text in values.items():
            card = self._trip_cards.get(key)
            if card is not None:
                card.set_value(
                    text,
                    accent=status_colors.get(state.status)
                    if key == "status"
                    else None,
                )

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total = max(0, round(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{secs:02d}"

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
        performance_values = {
            "rpm": None if self._state.engine_speed_rpm is None else self._state.engine_speed_rpm / 1000.0,
            "boost": self._state.boost_psi,
            "speed": self._state.speed_mph,
            "throttle": self._state.throttle_percent,
        }
        for gauge_id, gauge in self._gauges.items():
            gauge.set_connected(True)
            gauge.set_value(performance_values[gauge_id])

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
        self._apply_ecu_state()

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
