# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ECU dashboard matching the compact OpenRoadCode cockpit design."""

from __future__ import annotations

import tkinter as tk
import time
import math
from dataclasses import replace

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from ui.automotive.engine_analysis import (EngineAnalysis, EngineLoadLevel, FuelControlMode, FuelCorrectionStatus, MixtureMode, TrackingQuality)
from ui.automotive.vehicle_configuration import (VehicleConfiguration)
from ui.theme import ThemeBundle
from .ecu_engine_visual import paint_engine_visual, paint_engine_summary
from .ecu_engine_gl import create_engine_gl
from .ecu_card_layout import fit_ecu_card
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL


def visual_engine_running(rpm: float | None, analyzed_running: bool | None) -> bool | None:
    """Use current RPM for motion instead of waiting for a separate analysis update."""
    if rpm is not None and math.isfinite(rpm):
        return rpm >= 20.0 * 60.0 / math.tau
    return analyzed_running


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
        self._field_labels: dict[str, tk.Label] = {}
        self._animation_enabled = True
        self._animation_phase = 0.0
        self._animation_time = time.monotonic()
        self._engine_gl = None
        self._renderer_reason = ""
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

    def set_engine_animation(self, enabled: bool) -> None:
        """Pause visual motion without changing telemetry or engine status."""
        if enabled == self._animation_enabled:
            return
        self._animation_enabled = enabled
        self._paint_animation_status()
        if self._animation_job is not None:
            self.after_cancel(self._animation_job)
            self._animation_job = None
        if enabled:
            self._animation_time = time.monotonic()
            self._queue_engine_animation()

    def _visual_analysis(self) -> EngineAnalysis:
        running = visual_engine_running(self._vehicle_state.engine_speed_rpm,
                                        self._analysis.engine_running)
        return replace(self._analysis, engine_running=running)

    def _paint_animation_status(self) -> None:
        if not hasattr(self, "_animation_toggle"):
            return
        if not self._animation_enabled:
            status = "Off"
        elif self._visual_analysis().engine_running is None:
            status = "Waiting for RPM"
        elif not self._visual_analysis().engine_running:
            status = "Engine off"
        else:
            status = "On"
        self._animation_toggle.configure(text=f"Animation: {status}")

    def _schedule_engine_animation(self) -> None:
        self._animation_job = None
        if not self._animation_enabled or not self.winfo_exists():
            return
        now = time.monotonic()
        elapsed = min(0.1, now - self._animation_time)
        self._animation_time = now
        if self.winfo_ismapped() and self._visual_analysis().engine_running:
            rpm = self._vehicle_state.engine_speed_rpm or 0.0
            visual_hz = max(0.8, min(4.5, rpm / 900.0))
            self._animation_phase = (self._animation_phase + visual_hz * elapsed) % 2.0
            try:
                self._paint_engine()
            finally:
                # A draw callback must not permanently drop the animation timer.
                self._queue_engine_animation()
        else:
            self._queue_engine_animation()

    def _queue_engine_animation(self) -> None:
        if (self._animation_enabled and self.winfo_exists()
                and self._animation_job is None):
            self._animation_job = self.after(
                50 if self._engine_gl is not None else 83, self._schedule_engine_animation,
            )

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
        engine.place(relx=0.5, rely=0.5, relwidth=0.285, relheight=0.96, anchor="center")
        engine.grid_columnconfigure(0, weight=1)
        engine.grid_rowconfigure(0, weight=1)

        self._engine_canvas = tk.Canvas(
            engine, width=1, height=1, bg=ui.surface, highlightthickness=1,
            highlightbackground=ui.border, bd=0,
        )
        self._engine_canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=(5, 2))
        self._engine_canvas.bind("<Configure>", lambda _e: self._paint_engine())
        self._engine_gl = create_engine_gl(
            engine, theme=self._theme, on_failure=self._use_canvas_engine,
            on_unavailable=self._record_renderer_reason,
        )
        if self._engine_gl is not None:
            self._engine_canvas.grid_remove()
            self._engine_gl.grid(row=0, column=0, sticky="nsew", padx=2, pady=(5, 2))
        self._engine_summary = tk.Label(
            engine, text="--", fg=ui.text_muted, bg=ui.surface,
            font=("Sans", FONT_CONTROL, "bold"), pady=7,
        )
        self._engine_summary.grid(row=1, column=0, sticky="ew", padx=5, pady=(2, 5))
        self._engine_summary.bind(
            "<Configure>",
            lambda event: self._engine_summary.configure(wraplength=max(1, event.width - 10)),
        )

        self._animation_toggle = tk.Button(
            engine, text="Animation: On",
            command=lambda: self.set_engine_animation(not self._animation_enabled),
            bg=ui.surface_alt, fg=ui.text, activebackground=ui.surface,
            activeforeground=ui.text, highlightbackground=ui.border,
            font=("Sans", FONT_CONTROL, "bold"), bd=0, pady=9,
        )
        self._animation_toggle.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))

        self._renderer_status = tk.Label(
            engine, text="", fg=ui.text_muted, bg=ui.surface,
            font=("Sans", FONT_SMALL), pady=3,
        )
        self._renderer_status.grid(row=3, column=0, sticky="ew", padx=5)
        self._renderer_status.bind(
            "<Configure>",
            lambda event: self._renderer_status.configure(wraplength=max(1, event.width-10)),
        )
        self._record_renderer_reason(self._renderer_reason)

        # Keep telemetry cards outside the engine viewport so the complete
        # cutaway stays visible at every dashboard size.
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
        body.bind("<Configure>", lambda event: self._fit_card(body, event.width))
        return body

    def _fit_card(self, body: tk.Frame, width: int) -> None:
        fit_ecu_card(body, width, field_labels=self._field_labels,
                     labels=self._labels, bars=self._bars)

    def _value(self, parent: tk.Misc, row: int, key: str, label: str, *, status: bool = False) -> None:
        ui = self._theme.ui
        field = tk.Label(parent, text=label, fg=ui.text, bg=ui.surface,
                         font=("Sans", FONT_SMALL), anchor="w")
        field.grid(row=row, column=0, sticky="w", pady=2)
        field._full_text = label
        self._field_labels[key] = field
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
        self._paint_animation_status()
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

    def _record_renderer_reason(self, reason: str) -> None:
        self._renderer_reason = reason
        if hasattr(self, "_renderer_status"):
            self._renderer_status.configure(
                text=f"3D unavailable: {reason}" if reason else "",
            )

    def _use_canvas_engine(self) -> None:
        renderer, self._engine_gl = self._engine_gl, None
        if renderer is not None:
            renderer.destroy()
        self._engine_canvas.grid()
        self._paint_engine()

    def _paint_engine(self) -> None:
        if not hasattr(self, "_engine_canvas"):
            return
        if self._engine_gl is not None:
            self._engine_gl.update_engine(self._visual_analysis(), self._animation_phase)
            paint_engine_summary(self._engine_summary, self._analysis)
            return
        paint_engine_visual(
            self._engine_canvas,
            self._engine_summary,
            theme=self._theme,
            vehicle_state=self._vehicle_state,
            analysis=self._visual_analysis(),
            animation_phase=self._animation_phase,
        )

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
