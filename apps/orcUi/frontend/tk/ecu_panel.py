# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ECU dashboard matching the compact OpenRoadCode cockpit design."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from controllers.automotive import (
    EngineAnalysis,
    EngineLoadLevel,
    EngineOperatingMode,
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
    clamped = max(minimum, min(maximum, value))
    start = rail_start + radius
    end = rail_end - radius
    if maximum <= minimum:
        return (start + end) / 2.0
    return start + ((clamped - minimum) / (maximum - minimum)) * (end - start)


class EcuPanel(tk.Frame):
    """Dense driver-facing ECU interpretation dashboard."""

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
        self._bars: dict[str, tk.Canvas] = {}
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
        self.grid_rowconfigure(0, weight=1)

        cockpit = tk.Frame(self, bg=ui.background)
        cockpit.grid(row=0, column=0, sticky="nsew")
        # Let the engine-management story dominate the page. Side cards remain
        # glanceable, but the live flow schematic is now the visual anchor.
        cockpit.grid_columnconfigure(0, weight=27, uniform="ecu-side")
        cockpit.grid_columnconfigure(1, weight=46)
        cockpit.grid_columnconfigure(2, weight=27, uniform="ecu-side")
        cockpit.grid_rowconfigure(0, weight=1)

        left = tk.Frame(cockpit, bg=ui.background)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        center = tk.Frame(cockpit, bg=ui.background)
        center.grid(row=0, column=1, sticky="nsew", padx=4)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(1, weight=1)

        right = tk.Frame(cockpit, bg=ui.background)
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self._build_fuel(self._card(left, 0, 0, "⛽", "FUEL CONTROL", "Feedback and fuel correction", "#D6A800"))
        self._build_load(self._card(left, 1, 0, "◆", "ENGINE LOAD", "Demand, throttle and boost", "#D96A2B"))
        self._build_mixture(self._card(right, 0, 0, "λ", "MIXTURE", "Commanded vs. measured lambda", ui.accent_primary))
        self._build_ignition(self._card(right, 1, 0, "ϟ", "IGNITION", "Spark timing reported by ECU", ui.accent_success))

        self._engine_mode = tk.Label(
            center, text="--", fg=ui.text, bg=ui.surface,
            font=("Sans", 19, "bold"), pady=7,
        )
        self._engine_mode.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))
        self._engine_canvas = tk.Canvas(
            center, width=1, height=1, bg=ui.surface, highlightthickness=1,
            highlightbackground=ui.border, bd=0,
        )
        self._engine_canvas.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self._engine_canvas.bind("<Configure>", lambda _e: self._paint_engine())
        self._engine_summary = tk.Label(
            center, text="--", fg=ui.text_muted, bg=ui.surface,
            font=("Sans", FONT_CONTROL, "bold"), pady=7,
        )
        self._engine_summary.grid(row=2, column=0, sticky="ew", padx=5, pady=(2, 5))

    def _card(
        self, parent: tk.Misc, row: int, col: int, icon: str, title: str, subtitle: str, accent: str
    ) -> tk.Frame:
        ui = self._theme.ui
        card = tk.Frame(parent, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        tk.Frame(card, bg=accent, width=3).grid(row=0, column=0, rowspan=3, sticky="nsw")
        card.grid_columnconfigure(1, weight=1)
        tk.Label(card, text=icon, fg=accent, bg=ui.surface, font=("Sans", 18, "bold")).grid(
            row=0, column=0, rowspan=2, sticky="n", padx=(9, 6), pady=(7, 0)
        )
        tk.Label(card, text=title, fg=accent, bg=ui.surface, font=("Sans", 13, "bold"), anchor="w").grid(
            row=0, column=1, sticky="ew", pady=(6, 0)
        )
        tk.Label(card, text=subtitle, fg=ui.text_muted, bg=ui.surface, font=("Sans", FONT_SMALL), anchor="w").grid(
            row=1, column=1, sticky="ew", pady=(0, 5)
        )
        body = tk.Frame(card, bg=ui.surface)
        body.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=9, pady=(1, 5))
        card.grid_rowconfigure(2, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_columnconfigure(2, weight=2)
        return body

    def _value(self, parent: tk.Misc, row: int, key: str, label: str, *, status: bool = False) -> None:
        ui = self._theme.ui
        tk.Label(parent, text=label, fg=ui.text, bg=ui.surface, font=("Sans", FONT_SMALL), anchor="w").grid(
            row=row, column=0, sticky="w", pady=2
        )
        value = tk.Label(
            parent, text="--", fg=ui.accent_primary if not status else ui.accent_success,
            bg=ui.surface, font=("Sans", FONT_BODY, "bold"), anchor="e",
        )
        value.grid(row=row, column=1, sticky="e", padx=(3, 6), pady=2)
        self._labels[key] = value

    def _bar(self, parent: tk.Misc, row: int, key: str, *, height: int = 24) -> None:
        ui = self._theme.ui
        canvas = tk.Canvas(parent, width=1, height=max(height, 30), bg=ui.surface, highlightthickness=0, bd=0)
        canvas.grid(row=row, column=2, sticky="ew", pady=3)
        canvas.bind("<Configure>", lambda _e: self._paint_bars())
        self._bars[key] = canvas

    def _build_fuel(self, body: tk.Frame) -> None:
        ui = self._theme.ui
        mode = tk.Label(body, text="--", fg=ui.text, bg=ui.surface, font=("Sans", 15, "bold"), anchor="w")
        mode.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(1, 7))
        self._labels["fuel_mode"] = mode
        self._value(body, 1, "stft", "STFT (B1)")
        self._bar(body, 1, "stft")
        self._value(body, 2, "ltft", "LTFT (B1)")
        self._bar(body, 2, "ltft")
        self._value(body, 3, "fuel_status", "Fuel System", status=True)
        self._labels["fuel_status"].grid(columnspan=2, sticky="w")

    def _build_mixture(self, body: tk.Frame) -> None:
        mode = tk.Label(body, text="--", fg=self._theme.ui.text, bg=self._theme.ui.surface, font=("Sans", 15, "bold"), anchor="w")
        mode.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(1, 7))
        self._labels["mixture_mode"] = mode
        self._value(body, 1, "commanded", "Commanded λ")
        self._bar(body, 1, "commanded")
        self._value(body, 2, "measured", "Measured λ")
        self._bar(body, 2, "measured")
        self._value(body, 3, "mixture_status", "Tracking", status=True)
        self._labels["mixture_status"].grid(columnspan=2, sticky="w")

    def _build_load(self, body: tk.Frame) -> None:
        mode = tk.Label(body, text="--", fg=self._theme.ui.text, bg=self._theme.ui.surface, font=("Sans", 15, "bold"), anchor="w")
        mode.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(1, 7))
        self._labels["load_mode"] = mode
        self._value(body, 1, "load", "Engine Load")
        self._bar(body, 1, "load")
        self._value(body, 2, "boost", "Boost Pressure")
        self._bar(body, 2, "boost")
        self._value(body, 3, "throttle", "Throttle")
        self._bar(body, 3, "throttle")

    def _build_ignition(self, body: tk.Frame) -> None:
        mode = tk.Label(body, text="--", fg=self._theme.ui.text, bg=self._theme.ui.surface, font=("Sans", 15, "bold"), anchor="w")
        mode.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(1, 7))
        self._labels["ignition_mode"] = mode
        self._value(body, 1, "timing", "Timing Advance")
        self._bar(body, 1, "timing")
        self._value(body, 2, "ignition_status", "Timing Data", status=True)
        self._labels["ignition_status"].grid(columnspan=2, sticky="w")

    @staticmethod
    def _pct(value: float | None, signed: bool = False) -> str:
        if value is None:
            return "--"
        return f"{value:+.1f} %" if signed else f"{value:.0f} %"

    def _paint(self) -> None:
        state, analysis, ui = self._vehicle_state, self._analysis, self._theme.ui
        fuel_mode = {
            FuelControlMode.OPEN_LOOP_WARMUP: "Open Loop · Warm-up",
            FuelControlMode.CLOSED_LOOP: "Closed Loop",
            FuelControlMode.OPEN_LOOP_LOAD_OR_DECEL: "Open Loop · Load/Decel",
            FuelControlMode.OPEN_LOOP_FAULT: "Open Loop · Fault",
            FuelControlMode.CLOSED_LOOP_FAULT: "Closed Loop · Fault",
            FuelControlMode.UNKNOWN: "--",
        }[analysis.fuel_control_mode]
        correction = {
            FuelCorrectionStatus.NORMAL: "CL - Normal Operation",
            FuelCorrectionStatus.ADDING_FUEL: "Adding Fuel",
            FuelCorrectionStatus.REMOVING_FUEL: "Removing Fuel",
            FuelCorrectionStatus.UNKNOWN: "--",
        }[analysis.fuel_correction_status]
        mixture = {
            MixtureMode.RICH: "Rich",
            MixtureMode.STOICHIOMETRIC: "Stoichiometric",
            MixtureMode.LEAN: "Lean",
            MixtureMode.UNKNOWN: "--",
        }[analysis.mixture_mode]
        values = {
            "fuel_mode": fuel_mode.upper(),
            "mixture_mode": mixture.upper(),
            "load_mode": {
                EngineLoadLevel.LOW: "LOW LOAD",
                EngineLoadLevel.MODERATE: "MODERATE LOAD",
                EngineLoadLevel.HIGH: "HIGH LOAD",
                EngineLoadLevel.UNKNOWN: "--",
            }[analysis.load_level],
            "ignition_mode": "TIMING AVAILABLE" if state.ignition_timing_advance_deg is not None else "TIMING UNAVAILABLE",
            "stft": self._pct(state.short_term_fuel_trim_percent, True),
            "ltft": self._pct(state.long_term_fuel_trim_percent, True),
            "fuel_status": correction,
            "commanded": "--" if state.commanded_equivalence_ratio is None else f"{state.commanded_equivalence_ratio:.3f}",
            "measured": "--" if state.measured_equivalence_ratio is None else f"{state.measured_equivalence_ratio:.3f} λ",
            "mixture_status": {
                TrackingQuality.GOOD: "Tracking Good",
                TrackingQuality.MODERATE: "Tracking Moderate",
                TrackingQuality.POOR: "Tracking Poor",
                TrackingQuality.UNKNOWN: "--",
            }[analysis.mixture_tracking],
            "load": self._pct(state.engine_load_percent if state.engine_load_percent is not None else state.absolute_engine_load_percent),
            "boost": "--" if state.boost_psi is None else f"{state.boost_psi:.1f} PSI",
            "throttle": self._pct(state.throttle_percent),
            "timing": "--" if state.ignition_timing_advance_deg is None else f"{state.ignition_timing_advance_deg:.1f}° BTDC",
            "ignition_status": "ECU Reporting" if state.ignition_timing_advance_deg is not None else "--",
        }
        for key, value in values.items():
            self._labels[key].configure(text=value)
        self._labels["fuel_mode"].configure(
            fg=ui.accent_success if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP else ui.text
        )
        self._labels["mixture_mode"].configure(
            fg=ui.accent_success if analysis.mixture_mode is MixtureMode.STOICHIOMETRIC else ui.accent_primary
        )
        self._labels["load_mode"].configure(
            fg=ui.accent_success if analysis.load_level is EngineLoadLevel.LOW else "#D96A2B"
        )
        self._labels["ignition_mode"].configure(
            fg=ui.accent_success if state.ignition_timing_advance_deg is not None else ui.text_muted
        )
        self._paint_bars()
        self._paint_engine()

    def _paint_engine(self) -> None:
        if not hasattr(self, "_engine_canvas"):
            return
        canvas, analysis, state, ui = self._engine_canvas, self._analysis, self._vehicle_state, self._theme.ui
        canvas.delete("all")
        w, h = max(260, canvas.winfo_width()), max(260, canvas.winfo_height())
        sx, sy = w / 400.0, h / 430.0
        def box(x1, y1, x2, y2, *, fill, outline=None, width=2):
            canvas.create_rectangle(x1*sx, y1*sy, x2*sx, y2*sy, fill=fill, outline=outline or ui.border, width=width)
        def line(points, *, fill, width=5):
            canvas.create_line(*[v * (sx if i % 2 == 0 else sy) for i, v in enumerate(points)], fill=fill, width=width, smooth=True)

        active = ui.accent_success
        intake = ui.accent_primary if analysis.engine_running else ui.text_muted
        fuel = "#D6A800" if analysis.engine_running else ui.text_muted
        combustion = "#D96A2B" if analysis.engine_running else ui.surface_alt
        exhaust = ui.accent_danger if analysis.engine_running else ui.text_muted
        turbo = ui.accent_primary if analysis.forced_induction_active else ui.text_muted

        # Intake and turbo path.
        line((18, 105, 85, 105, 115, 125), fill=intake, width=8)
        canvas.create_text(20*sx, 84*sy, text="INTAKE", anchor="w", fill=ui.text_muted, font=("Sans", 8, "bold"))
        canvas.create_oval(100*sx, 104*sy, 146*sx, 150*sy, outline=turbo, width=5)
        canvas.create_arc(108*sx, 112*sy, 138*sx, 142*sy, start=20, extent=285, style="arc", outline=turbo, width=3)
        canvas.create_text(123*sx, 92*sy, text="TURBO", fill=turbo, font=("Sans", 8, "bold"))
        line((146, 127, 180, 145), fill=intake, width=7)

        # Engine block and head.
        box(150, 135, 330, 285, fill=ui.surface_alt, outline=ui.border, width=2)
        box(165, 115, 315, 155, fill=ui.surface_alt, outline=intake, width=2)
        canvas.create_text(240*sx, 133*sy, text="ENGINE", fill=ui.text, font=("Sans", 13, "bold"))

        # Fuel rail and injectors.
        line((170, 165, 310, 165), fill=fuel, width=5)
        for x in (185, 220, 255, 290):
            canvas.create_line(x*sx, 165*sy, x*sx, 190*sy, fill=fuel, width=4)
            canvas.create_polygon((x-5)*sx, 188*sy, (x+5)*sx, 188*sy, x*sx, 199*sy, fill=fuel, outline="")
        canvas.create_text(240*sx, 177*sy, text="FUEL RAIL / INJECTORS", fill=fuel, font=("Sans", 7, "bold"))

        # Four combustion chambers.
        load = state.engine_load_percent if state.engine_load_percent is not None else state.absolute_engine_load_percent
        chamber_fill = combustion if analysis.engine_running else ui.surface
        for x in (177, 217, 257, 297):
            canvas.create_oval((x-14)*sx, 205*sy, (x+14)*sx, 250*sy, fill=chamber_fill, outline=ui.border, width=2)
        canvas.create_text(240*sx, 267*sy, text="COMBUSTION", fill=combustion, font=("Sans", 8, "bold"))

        # Exhaust path and oxygen feedback loop.
        line((330, 230, 360, 250, 382, 250), fill=exhaust, width=8)
        canvas.create_text(380*sx, 270*sy, text="EXHAUST", anchor="e", fill=ui.text_muted, font=("Sans", 8, "bold"))
        if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP:
            canvas.create_oval(350*sx, 218*sy, 362*sx, 230*sy, fill=active, outline="")
            canvas.create_text(356*sx, 207*sy, text="O₂", fill=active, font=("Sans", 8, "bold"))

        # Semantic state badges beneath the schematic.
        badges = []
        if analysis.high_load:
            badges.append(("HIGH LOAD", "#D96A2B"))
        if analysis.forced_induction_active:
            badges.append(("BOOST", ui.accent_primary))
        if analysis.enrichment_active:
            badges.append(("ENRICHMENT", "#D6A800"))
        if analysis.warmed_up is False:
            badges.append(("WARM-UP", "#D6A800"))
        if not badges and analysis.engine_running:
            badges.append(("RUNNING", active))
        x = 200 - (len(badges) * 68) / 2
        for label, color in badges:
            canvas.create_rectangle(x*sx, 310*sy, (x+62)*sx, 334*sy, outline=color, width=2)
            canvas.create_text((x+31)*sx, 322*sy, text=label, fill=color, font=("Sans", 7, "bold"))
            x += 68

        mode = {
            EngineOperatingMode.OFF: "ENGINE OFF",
            EngineOperatingMode.IDLE: "IDLE",
            EngineOperatingMode.CRUISE: "CRUISE",
            EngineOperatingMode.ACCELERATION: "ACCELERATION",
            EngineOperatingMode.UNKNOWN: "ENGINE MANAGEMENT",
        }[analysis.operating_mode]
        self._engine_mode.configure(text=mode)

        fuel_mode = "CLOSED LOOP" if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP else "OPEN LOOP" if analysis.fuel_control_mode is not FuelControlMode.UNKNOWN else "--"
        mixture = {
            MixtureMode.RICH: "RICH",
            MixtureMode.STOICHIOMETRIC: "STOICH",
            MixtureMode.LEAN: "LEAN",
            MixtureMode.UNKNOWN: "--",
        }[analysis.mixture_mode]
        load_text = {
            EngineLoadLevel.LOW: "LOW LOAD",
            EngineLoadLevel.MODERATE: "MODERATE LOAD",
            EngineLoadLevel.HIGH: "HIGH LOAD",
            EngineLoadLevel.UNKNOWN: "--",
        }[analysis.load_level]
        tracking = {
            TrackingQuality.GOOD: "TRACKING GOOD",
            TrackingQuality.MODERATE: "TRACKING MODERATE",
            TrackingQuality.POOR: "TRACKING POOR",
            TrackingQuality.UNKNOWN: "",
        }[analysis.mixture_tracking]
        summary = " · ".join(part for part in (fuel_mode, mixture, load_text, tracking) if part and part != "--")
        self._engine_summary.configure(text=summary or "--")

    def _paint_bars(self) -> None:
        state, ui = self._vehicle_state, self._theme.ui
        specs = {
            "stft": (state.short_term_fuel_trim_percent, -25.0, 25.0, ui.accent_success, ("-25", "0", "+25")),
            "ltft": (state.long_term_fuel_trim_percent, -25.0, 25.0, ui.accent_success, ("-25", "0", "+25")),
            "commanded": (state.commanded_equivalence_ratio, 0.7, 1.3, ui.accent_primary, ("0.7", "1.0", "1.3")),
            "measured": (state.measured_equivalence_ratio, 0.7, 1.3, ui.accent_success, ("Rich", "Stoich", "Lean")),
            "load": (state.engine_load_percent if state.engine_load_percent is not None else state.absolute_engine_load_percent, 0.0, 100.0, ui.accent_success, ("0", "50", "100")),
            "boost": (state.boost_psi, -15.0, 30.0, ui.accent_primary, ("-15", "0", "30")),
            "throttle": (state.throttle_percent, 0.0, 100.0, ui.accent_success, ("0", "50", "100")),
            "timing": (state.ignition_timing_advance_deg, -20.0, 60.0, ui.accent_primary, ("-20", "20", "60")),
        }
        for key, (value, minimum, maximum, color, ticks) in specs.items():
            canvas = self._bars.get(key)
            if canvas is None:
                continue
            self._paint_bar(canvas, value, minimum, maximum, color, ticks)

    def _paint_bar(
        self, canvas: tk.Canvas, value: float | None, minimum: float, maximum: float,
        color: str, ticks: tuple[str, str, str],
    ) -> None:
        ui = self._theme.ui
        canvas.delete("all")
        width = max(60, canvas.winfo_width())
        x1, x2, y = 4.0, width - 4.0, 9.0
        segments, gap = 14, 2
        sw = ((x2 - x1) - gap * (segments - 1)) / segments
        fraction = None if value is None else max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))
        active = 0 if fraction is None else round(fraction * segments)
        for i in range(segments):
            sx1 = x1 + i * (sw + gap)
            canvas.create_rectangle(
                sx1, y - 6, sx1 + sw, y + 6,
                fill=color if i < active else ui.surface_alt,
                outline=ui.border,
            )
        if value is not None:
            mx = bounded_marker_x(value, minimum=minimum, maximum=maximum, rail_start=x1, rail_end=x2, radius=2)
            canvas.create_line(mx, y - 9, mx, y + 9, fill=ui.text, width=3)
        canvas.create_text(x1, 27, text=ticks[0], anchor="w", fill=ui.text_muted, font=("Sans", 8))
        canvas.create_text((x1 + x2) / 2, 27, text=ticks[1], fill=ui.text_muted, font=("Sans", 8))
        canvas.create_text(x2, 27, text=ticks[2], anchor="e", fill=ui.text_muted, font=("Sans", 8))
