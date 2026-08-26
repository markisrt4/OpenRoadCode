# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt Termux:API location reports to normalized navigation positions."""

from __future__ import annotations

import json
import subprocess
import threading
from datetime import datetime

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.position_source_if import PositionSourceIf, PositionStateCallback
from hardware_io.termux_api import TermuxLocationClient


class TermuxPositionAdapter(PositionSourceIf):
    """Poll Android location and publish normalized position snapshots."""

    def __init__(self, location: TermuxLocationClient, *, interval_seconds: float = 1.0) -> None:
        if interval_seconds <= 0.0:
            raise ValueError("interval_seconds must be greater than zero")
        self._location = location
        self._interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, callback: PositionStateCallback) -> None:
        if not self._location.is_available:
            raise RuntimeError("Termux:API location access is unavailable")
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(callback,),
            name="termux-position-adapter",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(2.0, self._interval_seconds + 1.0))
        self._thread = None

    def _run(self, callback: PositionStateCallback) -> None:
        while not self._stop_event.is_set():
            try:
                location = self._location.read()
                has_coordinates = location.latitude_deg is not None and location.longitude_deg is not None
                callback(PositionState(
                    received_at=datetime.now(),
                    latitude_deg=location.latitude_deg,
                    longitude_deg=location.longitude_deg,
                    altitude_m=location.altitude_m,
                    speed_mps=location.speed_mps,
                    course_deg=location.bearing_deg,
                    fix_mode=3 if has_coordinates and location.altitude_m is not None else (2 if has_coordinates else 1),
                    accuracy_m=location.accuracy_m,
                    source="termux-location",
                ))
            except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
                pass
            self._stop_event.wait(self._interval_seconds)
