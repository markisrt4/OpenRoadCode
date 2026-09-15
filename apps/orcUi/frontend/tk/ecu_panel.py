# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""2x2 ECU interpretation dashboard for orcUi."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from controllers.automotive import (
    EngineAnalysis,
    EngineLoadLevel,
    FuelControlMode,
    FuelCorrectionStatus,
    MixtureMode,
    TrackingQuality,
    VehicleConfiguration,
)
from ui.theme import ThemeBundle
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL


def bounded_marker_x(
    value: float,
    *,
    minimum: float,
    maximum: float,
    rail_start: float,
    rail_end: float,
    radius: float,
) -> float:
    """Map a bounded value so the marker body stays completely on the rail."""
    clamped = max(minimum, min(maximum, value))
    start = rail_start + radius
    end = rail_end - radius
    if maximum <= minimum:
        return (start + end) / 2.0
    fraction = (clamped - minimum) / (maximum - minimum)
    return start + fraction * (end - start)


class EcuPanel(tk.Frame):
    """Driver-facing interpretation of ECU state, not a raw PID viewer."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        theme: ThemeBundle,
        vehicle_configuration: VehicleConfiguration,
        vehicle_state: VehiclePresentationState,
        engine_analysis: EngineAnalysis,
    ) -> None:
        self._theme = theme
        self._vehicle_configuration = vehicle_configuration
        self._vehicle_state = vehicle_state
        self._analysis = engine_analysis
        self._labels: dict[str, tk.Label] = {}
        self._canvases: dict[str, tk.Canvas] = {}
        self._condition_labels: dict[str, tk.Label] = {}
        super().__init__(parent, bg=theme.ui.background)
        self._build()
        self._paint()

    def update_vehicle(self, state: VehiclePresentationState) -> None:
        self._vehicle_state = state
        self._paint()

    def update_analysis(self, analysis: EngineAnalysis) -> None:
        self._analysis = analysis
        self._paint()

    def _build(self) -> None:
        ui = self._theme.ui
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(
            self,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        header.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 6))
        marker = tk.Frame(header, bg=ui.accent_primary, width=5)
        marker.pack(side=tk.LEFT, fill=tk.Y)
        text = tk.Frame(header, bg=ui.surface_alt)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=14, pady=7)
        tk.Label(
            text,
            text="ECU MONITOR",
            fg=ui.text,
            bg=ui.surface_alt,
            font=("Sans", 16, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            text,
            text="What the engine computer is doing right now",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", FONT_SMALL),
            anchor="w",
        ).pack(anchor="w")

        grid = tk.Frame(self, bg=ui.background)
        grid.grid(row=1, column=0, sticky="nsew")
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1, uniform="ecu")
        for row in range(2):
            grid.grid_rowconfigure(row, weight=1, uniform="ecu")

        specs = (
            (0, 0, "FUEL CONTROL", ui.accent_warning, "fuel"),
            (0, 1, "MIXTURE", ui.accent_primary, "mixture"),
            (1, 0, "ENGINE LOAD", ui.accent_danger, "load"),
            (1, 1, "IGNITION TIMING", ui.accent_success, "ignition"),
        )
        for row, column, title, accent, key in specs:
            card = self._card(grid, title, accent)
            card.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
            self._build_card_content(card, key)

        footer = tk.Frame(
            self,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        footer.grid(row=2, column=0, sticky="ew", padx=4, pady=(4, 2))
        footer.grid_columnconfigure(1, weight=1)
        tk.Label(
            footer,
            text="ENGINE STATE",
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", FONT_SMALL, "bold"),
        ).grid(row=0, column=0, rowspan=2, sticky="w", padx=(14, 18), pady=8)
        mode = tk.Label(
            footer,
            text="--",
            fg=ui.accent_primary,
            bg=ui.surface_alt,
            font=("Sans", FONT_BODY + 1, "bold"),
            anchor="w",
        )
        mode.grid(row=0, column=1, sticky="w", pady=(6, 0))
        self._labels["operating_mode"] = mode

        conditions = tk.Frame(footer, bg=ui.surface_alt)
        conditions.grid(row=1, column=1, sticky="w", pady=(0, 6))
        names = ["HIGH LOAD", "ENRICHMENT", "WARM-UP"]
        if self._vehicle_configuration.induction.is_forced_induction:
            names.insert(1, "BOOST")
        for name in names:
            label = tk.Label(
                conditions,
                text="○ " + name,
                fg=ui.text_muted,
                bg=ui.surface_alt,
                font=("Sans", FONT_SMALL, "bold"),
            )
            label.pack(side=tk.LEFT, padx=(0, 14))
            self._condition_labels[name] = label

    def _card(self, parent: tk.Misc, title: str, accent: str) -> tk.Frame:
        ui = self._theme.ui
        card = tk.Frame(
            parent,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(4, weight=1)
        tk.Frame(card, bg=accent, height=4).grid(row=0, column=0, sticky="ew")
        tk.Label(
            card,
            text=title,
            fg=accent,
            bg=ui.surface,
            font=("Sans", FONT_CONTROL, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(8, 2))
        return card

    def _build_card_content(self, card: tk.Frame, key: str) -> None:
        ui = self._theme.ui
        primary = tk.Label(
            card,
            text="--",
            fg=ui.text,
            bg=ui.surface,
            font=("Sans", 18, "bold"),
            anchor="w",
        )
        primary.grid(row=2, column=0, sticky="ew", padx=14)
        secondary = tk.Label(
            card,
            text="--",
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", FONT_CONTROL, "bold"),
            anchor="w",
        )
        secondary.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 2))
        canvas = tk.Canvas(
            card,
            height=78,
            bg=ui.surface,
            highlightthickness=0,
            bd=0,
        )
        canvas.grid(row=4, column=0, sticky="nsew", padx=14, pady=(2, 8))
        canvas.bind("<Configure>", lambda _event: self._paint_visuals())
        self._labels[f"{key}_primary"] = primary
        self._labels[f"{key}_secondary"] = secondary
        self._canvases[key] = canvas

    def _paint(self) -> None:
        if not self._labels:
            return
        ui = self._theme.ui
        state = self._vehicle_state
        analysis = self._analysis

        fuel_mode = {
            FuelControlMode.OPEN_LOOP_WARMUP: "OPEN LOOP",
            FuelControlMode.CLOSED_LOOP: "CLOSED LOOP",
            FuelControlMode.OPEN_LOOP_LOAD_OR_DECEL: "OPEN LOOP",
            FuelControlMode.OPEN_LOOP_FAULT: "OPEN LOOP",
            FuelControlMode.CLOSED_LOOP_FAULT: "CLOSED LOOP",
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

        fuel_fault_flag = analysis.fuel_control_mode in {
            FuelControlMode.OPEN_LOOP_FAULT,
            FuelControlMode.CLOSED_LOOP_FAULT,
        }
        fuel_secondary = (
            f"FAULT FLAG · {correction}"
            if fuel_fault_flag and correction != "--"
            else "FAULT FLAG" if fuel_fault_flag
            else correction
        )
        values = {
            "fuel_primary": fuel_mode,
            "fuel_secondary": self._fuel_summary(fuel_secondary),
            "mixture_primary": mixture,
            "mixture_secondary": self._mixture_summary(tracking),
            "load_primary": load,
            "load_secondary": self._load_summary(),
            "ignition_primary": (
                "--"
                if state.ignition_timing_advance_deg is None
                else f"{state.ignition_timing_advance_deg:.1f}°"
            ),
            "ignition_secondary": "SPARK ADVANCE",
            "operating_mode": analysis.operating_mode.value.replace("_", " ").upper(),
        }
        for key, text in values.items():
            self._labels[key].configure(text=text)

        fuel_color = ui.text
        if fuel_fault_flag:
            fuel_color = ui.accent_warning
        elif analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP:
            fuel_color = ui.accent_success
        self._labels["fuel_primary"].configure(fg=fuel_color)
        self._labels["fuel_secondary"].configure(
            fg=ui.accent_warning if fuel_fault_flag else ui.text_muted
        )

        tracking_color = {
            TrackingQuality.GOOD: ui.accent_success,
            TrackingQuality.MODERATE: ui.accent_warning,
            TrackingQuality.POOR: ui.accent_danger,
        }.get(analysis.mixture_tracking, ui.text_muted)
        self._labels["mixture_secondary"].configure(fg=tracking_color)

        active = {
            "HIGH LOAD": analysis.high_load is True,
            "BOOST": analysis.forced_induction_active is True,
            "ENRICHMENT": analysis.enrichment_active is True,
            "WARM-UP": analysis.warmed_up is False,
        }
        for name, label in self._condition_labels.items():
            enabled = active[name]
            label.configure(
                fg=ui.accent_success if enabled else ui.text_muted,
                text=("● " if enabled else "○ ") + name,
            )
        self._paint_visuals()

    @staticmethod
    def _fmt_percent(value: float | None) -> str:
        return "--" if value is None else f"{value:+.1f}%"

    def _fuel_summary(self, status: str) -> str:
        state = self._vehicle_state
        return (
            f"{status}   ·   STFT {self._fmt_percent(state.short_term_fuel_trim_percent)}"
            f"   ·   LTFT {self._fmt_percent(state.long_term_fuel_trim_percent)}"
        )

    def _mixture_summary(self, tracking: str) -> str:
        state = self._vehicle_state
        commanded = (
            "--" if state.commanded_equivalence_ratio is None
            else f"{state.commanded_equivalence_ratio:.3f}"
        )
        measured = (
            "--" if state.measured_equivalence_ratio is None
            else f"{state.measured_equivalence_ratio:.3f}"
        )
        return f"{tracking}   ·   CMD λ {commanded}   ·   ACT λ {measured}"

    def _load_summary(self) -> str:
        state = self._vehicle_state
        load = "--" if state.absolute_engine_load_percent is None else f"{state.absolute_engine_load_percent:.0f}%"
        map_kpa = "--" if state.manifold_pressure_kpa is None else f"{state.manifold_pressure_kpa:.0f} kPa"
        throttle = "--" if state.throttle_percent is None else f"{state.throttle_percent:.0f}%"
        return f"LOAD {load}   ·   MAP {map_kpa}   ·   THROTTLE {throttle}"

    def _paint_visuals(self) -> None:
        self._paint_fuel()
        self._paint_mixture()
        self._paint_load()
        self._paint_ignition()

    def _rail_geometry(self, canvas: tk.Canvas) -> tuple[float, float, float]:
        width = max(180, canvas.winfo_width())
        return 22.0, width - 22.0, 39.0

    def _paint_fuel(self) -> None:
        canvas = self._canvases.get("fuel")
        if canvas is None:
            return
        ui = self._theme.ui
        state = self._vehicle_state
        canvas.delete("all")
        width = max(180, canvas.winfo_width())
        x1, x2 = 82.0, width - 22.0

        for row, (label, value, color) in enumerate((
            ("STFT", state.short_term_fuel_trim_percent, ui.accent_success),
            ("LTFT", state.long_term_fuel_trim_percent, ui.accent_primary),
        )):
            y = 22.0 + row * 34.0
            canvas.create_text(4, y, anchor="w", text=label, fill=ui.text_muted, font=("Sans", FONT_SMALL, "bold"))
            canvas.create_line(x1, y, x2, y, fill=ui.border, width=5)
            center = (x1 + x2) / 2.0
            canvas.create_line(center, y - 9, center, y + 9, fill=ui.text, width=2)
            if value is None:
                continue
            x = bounded_marker_x(value, minimum=-25.0, maximum=25.0, rail_start=x1, rail_end=x2, radius=6.0)
            canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=color, outline=ui.surface, width=2)
            canvas.create_text(x2, y - 11, anchor="e", text=f"{value:+.1f}%", fill=color, font=("Sans", FONT_SMALL, "bold"))

    def _paint_mixture(self) -> None:
        canvas = self._canvases.get("mixture")
        if canvas is None:
            return
        ui = self._theme.ui
        state = self._vehicle_state
        canvas.delete("all")
        x1, x2, y = self._rail_geometry(canvas)
        canvas.create_text(x1, 9, anchor="w", text="RICH", fill=ui.accent_warning, font=("Sans", FONT_SMALL, "bold"))
        canvas.create_text((x1 + x2) / 2, 9, text="STOICH", fill=ui.text, font=("Sans", FONT_SMALL, "bold"))
        canvas.create_text(x2, 9, anchor="e", text="LEAN", fill=ui.accent_primary, font=("Sans", FONT_SMALL, "bold"))
        canvas.create_line(x1, y, x2, y, fill=ui.border, width=4)
        markers = (
            ("T", state.commanded_equivalence_ratio, ui.accent_primary, -16),
            ("A", state.measured_equivalence_ratio, ui.accent_success, 16),
        )
        for label, value, color, offset in markers:
            if value is None:
                continue
            x = bounded_marker_x(
                value,
                minimum=0.70,
                maximum=1.30,
                rail_start=x1,
                rail_end=x2,
                radius=7.0,
            )
            canvas.create_line(x, y, x, y + offset, fill=color, width=2)
            canvas.create_oval(
                x - 7, y - 7, x + 7, y + 7,
                fill=color, outline=ui.surface, width=2,
            )
            canvas.create_text(
                x, y + offset * 1.55, text=label,
                fill=color, font=("Sans", FONT_SMALL, "bold"),
            )

    def _paint_load(self) -> None:
        canvas = self._canvases.get("load")
        if canvas is None:
            return
        ui = self._theme.ui
        state = self._vehicle_state
        canvas.delete("all")
        x1, x2, y = self._rail_geometry(canvas)
        canvas.create_text(x1, 9, anchor="w", text="0%", fill=ui.text_muted, font=("Sans", FONT_SMALL))
        canvas.create_text(x2, 9, anchor="e", text="150%", fill=ui.text_muted, font=("Sans", FONT_SMALL))
        segments = 16
        gap = 3
        segment_width = ((x2 - x1) - gap * (segments - 1)) / segments
        fraction = (
            None
            if state.absolute_engine_load_percent is None
            else max(0.0, min(1.0, state.absolute_engine_load_percent / 150.0))
        )
        active_count = 0 if fraction is None else round(fraction * segments)
        for index in range(segments):
            sx1 = x1 + index * (segment_width + gap)
            sx2 = sx1 + segment_width
            active = index < active_count
            canvas.create_rectangle(
                sx1, y - 7, sx2, y + 7,
                fill=ui.accent_danger if active else ui.surface_alt,
                outline=ui.accent_danger if active else ui.border,
            )
        value = state.absolute_engine_load_percent
        canvas.create_text(
            (x1 + x2) / 2, y + 25,
            text="--" if value is None else f"{value:.0f}%",
            fill=ui.text, font=("Sans", FONT_SMALL, "bold"),
        )

    def _paint_ignition(self) -> None:
        canvas = self._canvases.get("ignition")
        if canvas is None:
            return
        ui = self._theme.ui
        timing = self._vehicle_state.ignition_timing_advance_deg
        canvas.delete("all")
        x1, x2, y = self._rail_geometry(canvas)
        canvas.create_text(x1, 9, anchor="w", text="-20°", fill=ui.text_muted, font=("Sans", FONT_SMALL))
        canvas.create_text((x1 + x2) / 2, 9, text="0°", fill=ui.text_muted, font=("Sans", FONT_SMALL))
        canvas.create_text(x2, 9, anchor="e", text="+60°", fill=ui.text_muted, font=("Sans", FONT_SMALL))
        canvas.create_line(x1, y, x2, y, fill=ui.border, width=5)
        zero_x = x1 + 0.25 * (x2 - x1)
        canvas.create_line(zero_x, y - 11, zero_x, y + 11, fill=ui.text_muted, width=2)
        if timing is None:
            return
        x = bounded_marker_x(
            timing,
            minimum=-20.0,
            maximum=60.0,
            rail_start=x1,
            rail_end=x2,
            radius=7.0,
        )
        canvas.create_oval(
            x - 7, y - 7, x + 7, y + 7,
            fill=ui.accent_success, outline=ui.surface, width=2,
        )
        canvas.create_text(
            x, y + 22, text=f"{timing:+.1f}°",
            fill=ui.text, font=("Sans", FONT_SMALL, "bold"),
        )
