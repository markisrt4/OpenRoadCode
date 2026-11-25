# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ECU dashboard matching the compact OpenRoadCode cockpit design."""

from __future__ import annotations

import time
import tkinter as tk

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from ui.automotive.engine_analysis import (
    EngineAnalysis,
    EngineLoadLevel,
    FuelControlMode,
    FuelCorrectionStatus,
    MixtureMode,
    TrackingQuality,
)
from ui.automotive.vehicle_configuration import VehicleConfiguration
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget

from .ecu_animation import EcuAnimationMixin
from .ecu_animation import visual_engine_running as visual_engine_running
from .ecu_engine_visual import paint_engine_summary, paint_engine_visual
from .ecu_panel_layout import EcuPanelLayoutMixin
from .ecu_update_rate import RateCounter


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


class EcuPanel(EcuAnimationMixin, EcuPanelLayoutMixin, tk.Frame, UiWidget):
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
        self._rate_counter = RateCounter()
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

    def update_vehicle(self, state: VehiclePresentationState) -> None:
        self._rate_counter.record_update()
        self._vehicle_state = state
        self._paint()

    def update_analysis(self, analysis: EngineAnalysis) -> None:
        self._analysis = analysis
        self._paint()

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
            "ecu_power": "--"
            if analysis.reported_power_w is None
            else f"{analysis.reported_power_w / 745.699872:.1f} hp",
            "ecu_torque": "--"
            if analysis.reported_torque_nm is None
            else f"{analysis.reported_torque_nm:.0f} Nm",
            "fuel_mode": fuel_mode.upper(),
            "mixture_mode": f"TARGET: {mixture.upper()}" if mixture != "--" else "--",
            "load_mode": {
                EngineLoadLevel.LOW: "LOW LOAD",
                EngineLoadLevel.MODERATE: "MODERATE LOAD",
                EngineLoadLevel.HIGH: "HIGH LOAD",
                EngineLoadLevel.UNKNOWN: "--",
            }[analysis.load_level],
            "ignition_mode": "TIMING AVAILABLE"
            if state.ignition_timing_advance_deg is not None
            else "TIMING UNAVAILABLE",
            "stft": self._pct(state.short_term_fuel_trim_percent, True),
            "ltft": self._pct(state.long_term_fuel_trim_percent, True),
            "fuel_status": (
                f"Closed Loop · {correction}"
                if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP
                else f"{fuel_mode} · {correction}"
                if correction != "--"
                else fuel_mode
            ),
            "commanded": "--"
            if state.commanded_equivalence_ratio is None
            else f"{state.commanded_equivalence_ratio:.3f}",
            "measured": "--"
            if state.measured_equivalence_ratio is None
            else f"{state.measured_equivalence_ratio:.3f} λ",
            "mixture_status": {
                TrackingQuality.GOOD: "Tracking Good",
                TrackingQuality.MODERATE: "Tracking Moderate",
                TrackingQuality.POOR: "Tracking Poor",
                TrackingQuality.UNKNOWN: "--",
            }[analysis.mixture_tracking],
            "load": self._pct(
                state.engine_load_percent
                if state.engine_load_percent is not None
                else state.absolute_engine_load_percent
            ),
            "boost": "--" if state.boost_psi is None else f"{state.boost_psi:.1f} PSI",
            "throttle": self._pct(state.throttle_percent),
            "timing": "--"
            if state.ignition_timing_advance_deg is None
            else f"{state.ignition_timing_advance_deg:.1f}° BTDC",
            "ignition_status": (
                "Advance (+) / Retard (-)"
                if state.ignition_timing_advance_deg is not None
                else "--"
            ),
        }
        for key, value in values.items():
            self._labels[key].configure(text=value)
        self._labels["fuel_mode"].configure(
            fg=ui.accent_success
            if analysis.fuel_control_mode is FuelControlMode.CLOSED_LOOP
            else ui.text
        )
        self._labels["mixture_mode"].configure(
            fg=ui.accent_success
            if analysis.mixture_mode is MixtureMode.STOICHIOMETRIC
            else ui.accent_primary
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
        self._rate_counter.record_frame()

    def _paint_bars(self) -> None:
        state, ui = self._vehicle_state, self._theme.ui
        specs = {
            "stft": (
                state.short_term_fuel_trim_percent,
                -25.0,
                25.0,
                ui.accent_success,
                ("-25", "0", "+25"),
            ),
            "ltft": (
                state.long_term_fuel_trim_percent,
                -25.0,
                25.0,
                ui.accent_success,
                ("-25", "0", "+25"),
            ),
            "commanded": (
                state.commanded_equivalence_ratio,
                0.7,
                1.3,
                ui.accent_primary,
                ("0.7", "1.0", "1.3"),
            ),
            "measured": (
                state.measured_equivalence_ratio,
                0.7,
                1.3,
                ui.accent_success,
                ("Rich", "Stoich", "Lean"),
            ),
            "load": (
                state.engine_load_percent
                if state.engine_load_percent is not None
                else state.absolute_engine_load_percent,
                0.0,
                100.0,
                ui.accent_success,
                ("0", "50", "100"),
            ),
            "boost": (state.boost_psi, -15.0, 30.0, ui.accent_primary, ("-15", "0", "30")),
            "throttle": (state.throttle_percent, 0.0, 100.0, ui.accent_success, ("0", "50", "100")),
            "timing": (
                state.ignition_timing_advance_deg,
                -20.0,
                60.0,
                ui.accent_primary,
                ("-20", "20", "60"),
            ),
        }
        for key, (value, minimum, maximum, color, ticks) in specs.items():
            canvas = self._bars.get(key)
            if canvas is None:
                continue
            self._paint_bar(canvas, value, minimum, maximum, color, ticks)

    def _paint_bar(
        self,
        canvas: tk.Canvas,
        value: float | None,
        minimum: float,
        maximum: float,
        color: str,
        ticks: tuple[str, str, str],
    ) -> None:
        ui = self._theme.ui
        canvas.delete("all")
        width = max(60, canvas.winfo_width())
        x1, x2, y = 4.0, width - 4.0, 9.0
        segments, gap = 14, 2
        sw = ((x2 - x1) - gap * (segments - 1)) / segments
        fraction = (
            None if value is None else max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))
        )
        active = 0 if fraction is None else round(fraction * segments)
        for i in range(segments):
            sx1 = x1 + i * (sw + gap)
            canvas.create_rectangle(
                sx1,
                y - 6,
                sx1 + sw,
                y + 6,
                fill=color if i < active else ui.surface_alt,
                outline=ui.border,
            )
        if value is not None:
            mx = bounded_marker_x(
                value, minimum=minimum, maximum=maximum, rail_start=x1, rail_end=x2, radius=2
            )
            canvas.create_line(mx, y - 9, mx, y + 9, fill=ui.text, width=3)
        canvas.create_text(x1, 27, text=ticks[0], anchor="w", fill=ui.text_muted, font=("Sans", 8))
        canvas.create_text((x1 + x2) / 2, 27, text=ticks[1], fill=ui.text_muted, font=("Sans", 8))
        canvas.create_text(x2, 27, text=ticks[2], anchor="e", fill=ui.text_muted, font=("Sans", 8))
