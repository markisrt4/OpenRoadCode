# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ECU dashboard matching the compact OpenRoadCode cockpit design."""

from __future__ import annotations

import math
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
        self._animation_phase = 0.0
        self._animation_job: str | None = None
        super().__init__(parent, bg=theme.ui.background)
        self._build()
        self._paint()
        self._schedule_engine_animation()

    def destroy(self) -> None:
        if self._animation_job is not None:
            try:
                self.after_cancel(self._animation_job)
            except tk.TclError:
                pass
            self._animation_job = None
        super().destroy()

    def _schedule_engine_animation(self) -> None:
        if not self.winfo_exists():
            return
        if self._analysis.engine_running:
            rpm = self._vehicle_state.engine_speed_rpm or 0.0
            visual_hz = max(0.8, min(4.5, rpm / 900.0))
            self._animation_phase = (self._animation_phase + visual_hz / 12.0) % 1.0
            self._paint_engine()
        self._animation_job = self.after(83, self._schedule_engine_animation)

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

        # One composition surface lets the four cards frame the powertrain
        # instead of forcing the engine into a narrow middle column.
        cockpit = tk.Frame(self, bg=ui.background, width=640, height=420)
        cockpit.grid(row=0, column=0, sticky="nsew")

        engine = tk.Frame(cockpit, bg=ui.background)
        engine.place(relx=0.5, rely=0.5, relwidth=0.44, relheight=0.96, anchor="center")
        engine.grid_columnconfigure(0, weight=1)
        engine.grid_rowconfigure(0, weight=1)

        self._engine_canvas = tk.Canvas(
            engine, width=1, height=1, bg=ui.surface, highlightthickness=1,
            highlightbackground=ui.border, bd=0,
        )
        self._engine_canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=(5, 2))
        self._engine_canvas.bind("<Configure>", lambda _e: self._paint_engine())
        self._engine_summary = tk.Label(
            engine, text="--", fg=ui.text_muted, bg=ui.surface,
            font=("Sans", FONT_CONTROL, "bold"), pady=7,
        )
        self._engine_summary.grid(row=1, column=0, sticky="ew", padx=5, pady=(2, 5))

        # Cards intentionally overlap the outer edges of the engine surface.
        # This creates the surrounding composition from the concept while
        # keeping each card a normal Tk widget with its existing telemetry.
        fuel = self._floating_card(
            cockpit, relx=0.005, rely=0.01, relwidth=0.35, relheight=0.475,
            icon="⛽", title="FUEL CONTROL", subtitle="Feedback and fuel correction", accent="#D6A800",
        )
        load = self._floating_card(
            cockpit, relx=0.005, rely=0.515, relwidth=0.35, relheight=0.475,
            icon="◆", title="ENGINE LOAD", subtitle="Demand, throttle and boost", accent="#D96A2B",
        )
        mixture = self._floating_card(
            cockpit, relx=0.645, rely=0.01, relwidth=0.35, relheight=0.475,
            icon="λ", title="MIXTURE", subtitle="Commanded vs. measured lambda", accent=ui.accent_primary,
        )
        ignition = self._floating_card(
            cockpit, relx=0.645, rely=0.515, relwidth=0.35, relheight=0.475,
            icon="ϟ", title="IGNITION", subtitle="Spark timing reported by ECU", accent=ui.accent_success,
        )
        self._build_fuel(fuel)
        self._build_load(load)
        self._build_mixture(mixture)
        self._build_ignition(ignition)


    def _floating_card(
        self,
        parent: tk.Misc,
        *,
        relx: float,
        rely: float,
        relwidth: float,
        relheight: float,
        icon: str,
        title: str,
        subtitle: str,
        accent: str,
    ) -> tk.Frame:
        ui = self._theme.ui
        card = tk.Frame(parent, bg=ui.surface, highlightthickness=1, highlightbackground=accent)
        card.place(relx=relx, rely=rely, relwidth=relwidth, relheight=relheight)
        card.lift()
        tk.Frame(card, bg=accent, width=3).grid(row=0, column=0, rowspan=3, sticky="nsw")
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(2, weight=1)
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
        self._value(
            body, 1, "load",
            "Calculated Load" if self._vehicle_state.engine_load_percent is not None else "Absolute Load",
        )
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
            "mixture_mode": f"TARGET: {mixture.upper()}" if mixture != "--" else "--",
            "load_mode": {
                EngineLoadLevel.LOW: "LOW LOAD",
                EngineLoadLevel.MODERATE: "MODERATE LOAD",
                EngineLoadLevel.HIGH: "HIGH LOAD",
                EngineLoadLevel.UNKNOWN: "--",
            }[analysis.load_level],
            "ignition_mode": "TIMING AVAILABLE" if state.ignition_timing_advance_deg is not None else "TIMING UNAVAILABLE",
            "stft": self._pct(state.short_term_fuel_trim_percent, True),
            "ltft": self._pct(state.long_term_fuel_trim_percent, True),
            "fuel_status": (
                f"Closed Loop · {correction}"
                if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP
                else f"{fuel_mode} · {correction}" if correction != "--" else fuel_mode
            ),
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
            "ignition_status": (
                "Advance (+) / Retard (-)"
                if state.ignition_timing_advance_deg is not None else "--"
            ),
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
        sx, sy = w / 400.0, h / 360.0

        def line(points, *, fill, width=5):
            canvas.create_line(
                *[v * (sx if i % 2 == 0 else sy) for i, v in enumerate(points)],
                fill=fill, width=width, smooth=True,
            )

        active = ui.accent_success
        intake = ui.accent_primary if analysis.engine_running else ui.text_muted
        fuel = "#D6A800" if analysis.engine_running else ui.text_muted
        combustion = "#D96A2B" if analysis.engine_running else ui.surface_alt
        exhaust = ui.accent_danger if analysis.engine_running else ui.text_muted
        turbo = ui.accent_primary if analysis.forced_induction_active else ui.text_muted

        # Turbo sits above the engine. Blue is the compressor/intake path;
        # red is the exhaust/turbine path. Both meet at the shared turbo shaft.
        turbo_x, turbo_y = 200, 70
        canvas.create_text(200*sx, 25*sy, text="TURBO", fill=turbo, font=("Sans", 8, "bold"))
        canvas.create_oval(174*sx, 44*sy, 226*sx, 96*sy, outline=turbo, width=5)
        cx, cy = turbo_x*sx, turbo_y*sy
        turbo_phase = self._animation_phase * math.tau
        for blade in range(5):
            angle = turbo_phase + blade * math.tau / 5.0
            canvas.create_line(
                cx, cy, cx + math.cos(angle)*16*sx, cy + math.sin(angle)*16*sy,
                fill=turbo, width=2,
            )
        canvas.create_oval(194*sx, 64*sy, 206*sx, 76*sy, fill=turbo, outline="")

        canvas.create_text(120*sx, 50*sy, text="INTAKE", fill=ui.text_muted, font=("Sans", 7, "bold"))
        line((112, 61, 145, 61, 174, 68), fill=intake, width=7)
        line((200, 96, 200, 110, 164, 122), fill=intake, width=7)
        if analysis.engine_running:
            for offset in (0.0, 0.34, 0.68):
                travel = (self._animation_phase + offset) % 1.0
                px = (116 + 55 * travel) * sx
                py = (61 + 7 * max(0.0, (travel - 0.55) / 0.45)) * sy
                canvas.create_oval(px-3, py-3, px+3, py+3, fill=intake, outline="")

        # Larger, centered engine now that the old left-side turbo no longer
        # consumes the composition.
        canvas.create_polygon(
            116*sx, 112*sy, 284*sx, 112*sy, 300*sx, 128*sy,
            294*sx, 158*sy, 106*sx, 158*sy, 100*sx, 130*sy,
            fill=ui.surface_alt, outline=intake, width=2,
        )
        canvas.create_text(200*sx, 136*sy, text="ENGINE", fill=ui.text, font=("Sans", 14, "bold"))
        canvas.create_polygon(
            108*sx, 158*sy, 292*sx, 158*sy, 306*sx, 205*sy,
            292*sx, 270*sy, 108*sx, 270*sy, 94*sx, 205*sy,
            fill=ui.surface_alt, outline=ui.border, width=2,
        )
        canvas.create_rectangle(116*sx, 160*sy, 284*sx, 190*sy, fill=ui.surface, outline=ui.border, width=1)

        line((126, 170, 274, 170), fill=fuel, width=5)
        canvas.create_text(200*sx, 164*sy, text="FUEL RAIL", fill=fuel, font=("Sans", 7, "bold"), anchor="s")
        cylinders = (132, 177, 223, 268)
        for x in cylinders:
            canvas.create_line(x*sx, 171*sy, x*sx, 195*sy, fill=fuel, width=3)
            canvas.create_polygon(
                (x-4)*sx, 192*sy, (x+4)*sx, 192*sy, x*sx, 201*sy,
                fill=fuel, outline="",
            )
            canvas.create_rectangle(
                (x-15)*sx, 199*sy, (x+15)*sx, 249*sy,
                fill=ui.surface, outline=ui.border, width=2,
            )
            glow = combustion if analysis.engine_running else ui.surface_alt
            canvas.create_oval(
                (x-10)*sx, 211*sy, (x+10)*sx, 231*sy,
                fill=glow, outline=ui.text_muted, width=1,
            )
            canvas.create_line(x*sx, 231*sy, x*sx, 257*sy, fill=ui.text_muted, width=2)

        # Compact exhaust plumbing: runners feed the turbine, then a thin
        # downpipe passes the O2 sensor and catalyst. It should explain the
        # turbo relationship without visually wrapping the whole engine.
        collector_x, collector_y = 286, 252
        for x in cylinders:
            canvas.create_line(
                x*sx, 249*sy, x*sx, 253*sy, collector_x*sx, collector_y*sy,
                fill=exhaust, width=2, smooth=True,
            )
        line((collector_x, collector_y, 304, 230, 304, 118, 224, 78), fill=exhaust, width=3)
        line((226, 72, 282, 76, 300, 94, 300, 274), fill=exhaust, width=3)

        canvas.create_polygon(
            288*sx, 272*sy, 294*sx, 268*sy, 306*sx, 268*sy, 312*sx, 272*sy,
            312*sx, 286*sy, 306*sx, 290*sy, 294*sx, 290*sy, 288*sx, 286*sy,
            fill=ui.surface_alt, outline=exhaust, width=1,
        )
        canvas.create_text(300*sx, 279*sy, text="CAT", fill=ui.text, font=("Sans", 6, "bold"))
        line((300, 290, 300, 302, 282, 302), fill=exhaust, width=3)
        if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP:
            canvas.create_oval(296*sx, 250*sy, 304*sx, 258*sy, fill=active, outline="")
            canvas.create_text(300*sx, 244*sy, text="O₂", fill=active, font=("Sans", 7, "bold"))

        # A crank pulley and two accessory pulleys add smooth mechanical motion
        # without flashing or moving the cylinders. Rotation is driven by the
        # same RPM-scaled phase as the turbo.
        crank_x, crank_y = 200, 270
        accessory_y = 259
        belt = ui.text_muted
        canvas.create_line(200*sx, 270*sy, 157*sx, accessory_y*sy, 243*sx, accessory_y*sy, 200*sx, 270*sy,
                           fill=belt, width=2, smooth=True)
        for px, py, radius in ((157, accessory_y, 10), (243, accessory_y, 10), (crank_x, crank_y, 16)):
            canvas.create_oval(
                (px-radius)*sx, (py-radius)*sy, (px+radius)*sx, (py+radius)*sy,
                fill=ui.surface, outline=ui.border, width=2,
            )
        crank_phase = self._animation_phase * math.tau
        for blade in range(4):
            angle = crank_phase + blade * math.tau / 4.0
            canvas.create_line(
                crank_x*sx, crank_y*sy,
                (crank_x + math.cos(angle)*12)*sx,
                (crank_y + math.sin(angle)*12)*sy,
                fill=intake if analysis.engine_running else ui.text_muted, width=2,
            )
        for px, direction in ((157, -1.0), (243, 1.0)):
            angle = direction * crank_phase
            canvas.create_line(
                px*sx, accessory_y*sy,
                (px + math.cos(angle)*7)*sx,
                (accessory_y + math.sin(angle)*7)*sy,
                fill=ui.text_muted, width=2,
            )

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
