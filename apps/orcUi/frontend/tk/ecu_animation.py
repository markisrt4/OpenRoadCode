# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Animation lifecycle for the ECU dashboard."""

import math
import time
from dataclasses import replace

from ui.automotive.engine_analysis import EngineAnalysis


def visual_engine_running(rpm: float | None, analyzed_running: bool | None) -> bool | None:
    """Use current RPM for motion instead of waiting for a separate analysis update."""
    if rpm is not None and math.isfinite(rpm):
        return rpm >= 20.0 * 60.0 / math.tau
    return analyzed_running


class EcuAnimationMixin:
    """Own the pause/resume timer without synchronously drawing from controls."""

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

