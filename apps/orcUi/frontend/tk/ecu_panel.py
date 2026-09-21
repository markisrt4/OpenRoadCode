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
        engine.place(relx=0.5, rely=0.5, relwidth=0.48, relheight=0.96, anchor="center")
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
            cockpit, relx=0.005, rely=0.01, relwidth=0.335, relheight=0.475,
            icon="⛽", title="FUEL CONTROL", subtitle="Feedback and fuel correction", accent="#D6A800",
        )
        load = self._floating_card(
            cockpit, relx=0.005, rely=0.515, relwidth=0.335, relheight=0.475,
            icon="◆", title="ENGINE LOAD", subtitle="Demand, throttle and boost", accent="#D96A2B",
        )
        mixture = self._floating_card(
            cockpit, relx=0.66, rely=0.01, relwidth=0.335, relheight=0.475,
            icon="λ", title="MIXTURE", subtitle="Commanded vs. measured lambda", accent=ui.accent_primary,
        )
        ignition = self._floating_card(
            cockpit, relx=0.66, rely=0.515, relwidth=0.335, relheight=0.475,
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
        # The original drawing occupied only the upper half of the available
        # canvas. Scale the useful 360-unit schematic to the live viewport.
        sx, sy = w / 400.0, h / 360.0
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

        # Stack the intake above the turbo so the flow path uses the upper
        # left corner instead of consuming a long strip of horizontal space.
        canvas.create_text(88*sx, 42*sy, text="INTAKE", fill=ui.text_muted, font=("Sans", 8, "bold"))
        line((88, 52, 88, 82, 112, 100), fill=intake, width=8)
        if analysis.engine_running:
            for offset in (0.0, 0.33, 0.66):
                travel = (self._animation_phase + offset) % 1.0
                fy = (55 + 39 * travel) * sy
                canvas.create_oval(84*sx, fy-3, 92*sx, fy+3, fill=intake, outline="")
        canvas.create_oval(90*sx, 86*sy, 136*sx, 132*sy, outline=turbo, width=5)
        cx, cy = 113*sx, 109*sy
        turbo_phase = self._animation_phase * math.tau
        for blade in range(5):
            angle = turbo_phase + blade * math.tau / 5.0
            canvas.create_line(cx, cy, cx + math.cos(angle)*14*sx, cy + math.sin(angle)*14*sy, fill=turbo, width=2)
        canvas.create_oval(108*sx, 104*sy, 118*sx, 114*sy, fill=turbo, outline="")
        canvas.create_text(113*sx, 76*sy, text="TURBO", fill=turbo, font=("Sans", 8, "bold"))
        line((136, 109, 160, 128), fill=intake, width=7)

        # Stylized powertrain: valve cover/head, tapered block, fuel rail,
        # cylinders and exhaust manifold. Keep it graphical at dashboard scale.
        canvas.create_polygon(
            154*sx, 116*sy, 316*sx, 116*sy, 329*sx, 132*sy,
            323*sx, 158*sy, 157*sx, 158*sy, 148*sx, 137*sy,
            fill=ui.surface_alt, outline=intake, width=2,
        )
        canvas.create_text(238*sx, 137*sy, text="ENGINE", fill=ui.text, font=("Sans", 13, "bold"))
        canvas.create_oval(170*sx, 123*sy, 198*sx, 151*sy, outline=ui.border, width=2)

        # Cylinder head and lower block.
        canvas.create_polygon(
            153*sx, 158*sy, 326*sx, 158*sy, 337*sx, 199*sy,
            327*sx, 276*sy, 160*sx, 276*sy, 145*sx, 204*sy,
            fill=ui.surface_alt, outline=ui.border, width=2,
        )
        box(158, 160, 324, 190, fill=ui.surface, outline=ui.border, width=1)

        # Fuel rail sits above the injectors instead of sharing their label area.
        line((168, 170, 314, 170), fill=fuel, width=5)
        canvas.create_text(241*sx, 164*sy, text="FUEL RAIL", fill=fuel, font=("Sans", 7, "bold"), anchor="s")
        for x in (178, 220, 262, 304):
            canvas.create_line(x*sx, 171*sy, x*sx, 195*sy, fill=fuel, width=3)
            canvas.create_polygon(
                (x-4)*sx, 192*sy, (x+4)*sx, 192*sy, x*sx, 201*sy,
                fill=fuel, outline="",
            )

        # Cylinders are deliberately subdued; combustion is indicated by a
        # smaller glow so the block remains readable instead of becoming four
        # orange lamps.
        load = state.engine_load_percent if state.engine_load_percent is not None else state.absolute_engine_load_percent
        piston_phases = (0.0, 0.5, 0.5, 0.0)
        for index, x in enumerate((178, 220, 262, 304)):
            canvas.create_rectangle(
                (x-14)*sx, 199*sy, (x+14)*sx, 249*sy,
                fill=ui.surface, outline=ui.border, width=2,
            )
            phase = (self._animation_phase + piston_phases[index]) % 1.0
            piston_y = 217.0 if not analysis.engine_running else 217.0 + 12.0 * math.sin(phase * math.tau)
            glow = combustion if analysis.engine_running else ui.surface_alt
            canvas.create_oval(
                (x-9)*sx, (piston_y-10)*sy, (x+9)*sx, (piston_y+10)*sy,
                fill=glow, outline=ui.text_muted, width=1,
            )
            canvas.create_line(x*sx, (piston_y+10)*sy, x*sx, 257*sy, fill=ui.text_muted, width=2)

        # Four exhaust runners converge into a common collector before leaving
        # the engine. This reads much more like a manifold than one red pipe.
        manifold_y = 266
        for x in (178, 220, 262, 304):
            canvas.create_line(
                x*sx, 249*sy, x*sx, 256*sy, 326*sx, manifold_y*sy,
                fill=exhaust, width=3, smooth=True,
            )
        line((326, manifold_y, 344, 250), fill=exhaust, width=7)
        canvas.create_polygon(
            344*sx, 239*sy, 350*sx, 233*sy, 374*sx, 233*sy, 382*sx, 239*sy,
            382*sx, 257*sy, 374*sx, 263*sy, 350*sx, 263*sy, 344*sx, 257*sy,
            fill=ui.surface_alt, outline=exhaust, width=2,
        )
        line((382, 248, 396, 248), fill=exhaust, width=7)
        canvas.create_text(363*sx, 276*sy, text="CAT", fill=ui.text_muted, font=("Sans", 7, "bold"))
        if analysis.engine_running:
            pulse = (self._animation_phase * 3.0) % 1.0
            px = (328 + 66 * pulse) * sx
            canvas.create_oval(px-3, 245*sy, px+3, 251*sy, fill=exhaust, outline="")
        if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP:
            canvas.create_oval(337*sx, 232*sy, 349*sx, 244*sy, fill=active, outline="")
            canvas.create_text(343*sx, 221*sy, text="O₂", fill=active, font=("Sans", 8, "bold"))

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
            canvas.create_rectangle(x*sx, 304*sy, (x+62)*sx, 330*sy, outline=color, width=2)
            canvas.create_text((x+31)*sx, 317*sy, text=label, fill=color, font=("Sans", 7, "bold"))
            x += 68

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
