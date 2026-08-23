# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Simulated geographic position source for navigation development."""

from __future__ import annotations

import math
import threading
import time

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.position_source_if import PositionSourceIf, PositionStateCallback


class SimulatedPositionSource(PositionSourceIf):
    """Publish deterministic position updates without a GPS receiver."""

    def __init__(
        self,
        profile: str = "driving",
        latitude_deg: float = 42.8028,
        longitude_deg: float = -83.0127,
        speed_mps: float = 13.4,
        course_deg: float = 180.0,
        update_rate_hz: float = 5.0,
    ) -> None:
        if update_rate_hz <= 0:
            raise ValueError("update_rate_hz must be greater than zero")
        self._profile = profile.strip().lower()
        self._latitude_deg = latitude_deg
        self._longitude_deg = longitude_deg
        self._speed_mps = speed_mps
        self._course_deg = course_deg
        self._period_s = 1.0 / update_rate_hz
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, callback: PositionStateCallback) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(callback,),
            name="simulated-position",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(1.0, self._period_s * 2.0))
        self._thread = None

    def _run(self, callback: PositionStateCallback) -> None:
        phase = 0.0
        while not self._stop_event.is_set():
            if self._profile == "stationary":
                latitude = self._latitude_deg
                longitude = self._longitude_deg
                speed = 0.0
                course = self._course_deg
            elif self._profile == "driving":
                phase += 0.04
                latitude = self._latitude_deg + 0.002 * math.sin(phase)
                longitude = self._longitude_deg + 0.002 * math.cos(phase)
                speed = self._speed_mps + 1.5 * math.sin(phase * 2.0)
                course = (self._course_deg + math.degrees(phase)) % 360.0
            else:
                raise ValueError(f"unsupported simulated GPS profile: {self._profile}")

            callback(
                PositionState(
                    latitude_deg=latitude,
                    longitude_deg=longitude,
                    altitude_m=180.0 + 8.0 * math.sin(phase * 0.5),
                    speed_mps=max(0.0, speed),
                    course_deg=course,
                    fix_mode=3,
                    satellites_visible=12,
                    satellites_used=9,
                    accuracy_m=3.0,
                    source="simulation",
                )
            )
            self._stop_event.wait(self._period_s)
