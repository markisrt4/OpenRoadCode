# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Simulated ground-motion source for navigation development."""

from __future__ import annotations

import math
import threading

from controllers.navigation.ground_motion_source_if import (
    GroundMotionSourceIf,
    GroundMotionStateCallback,
)
from controllers.navigation.navigation_state import GroundMotionState


class SimulatedGroundMotionSource(GroundMotionSourceIf):
    """Publish deterministic speed and course updates without a receiver."""

    def __init__(
        self,
        profile: str = "driving",
        speed_mps: float = 13.4,
        course_deg: float = 180.0,
        update_rate_hz: float = 5.0,
    ) -> None:
        if update_rate_hz <= 0:
            raise ValueError("update_rate_hz must be greater than zero")
        self._profile = profile.strip().lower()
        self._speed_mps = speed_mps
        self._course_deg = course_deg
        self._period_s = 1.0 / update_rate_hz
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, callback: GroundMotionStateCallback) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(callback,),
            name="simulated-ground-motion",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(1.0, self._period_s * 2.0))
        self._thread = None

    def _run(self, callback: GroundMotionStateCallback) -> None:
        phase = 0.0
        while not self._stop_event.is_set():
            if self._profile == "stationary":
                speed_mps = 0.0
                course_deg = self._course_deg
            elif self._profile == "driving":
                phase += 0.04
                speed_mps = self._speed_mps + 1.5 * math.sin(phase)
                course_deg = (self._course_deg + 8.0 * math.sin(phase * 0.5)) % 360.0
            else:
                raise ValueError(
                    f"unsupported simulated ground-motion profile: {self._profile}"
                )

            callback(
                GroundMotionState(
                    speed_mps=speed_mps,
                    course_deg=course_deg,
                    source="simulation",
                )
            )
            self._stop_event.wait(self._period_s)
