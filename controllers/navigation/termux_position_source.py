# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Geographic position source backed by Termux:API location."""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
from collections.abc import Callable
from datetime import datetime

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.position_source_if import PositionSourceIf, PositionStateCallback


class TermuxPositionSource(PositionSourceIf):
    """Poll Android location through Termux:API and publish normalized fixes."""

    def __init__(self, *, interval_seconds: float = 1.0) -> None:
        if interval_seconds <= 0.0:
            raise ValueError("interval_seconds must be greater than zero")
        self._interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, callback: PositionStateCallback) -> None:
        if shutil.which("termux-location") is None:
            raise RuntimeError("termux-location is not available; install Termux:API and the termux-api package")
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(callback,),
            name="termux-position-source",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(2.0, self._interval_seconds + 1.0))
        self._thread = None

    def _run(self, callback: Callable[[PositionState], None]) -> None:
        while not self._stop_event.is_set():
            try:
                callback(self._read_position())
            except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
                # A temporary Android location failure should not kill the source thread.
                pass
            self._stop_event.wait(self._interval_seconds)

    @staticmethod
    def _read_position() -> PositionState:
        result = subprocess.run(
            ["termux-location", "-p", "gps", "-r", "once"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        payload = json.loads(result.stdout)
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        altitude = payload.get("altitude")
        speed = payload.get("speed")
        bearing = payload.get("bearing")
        accuracy = payload.get("accuracy")

        has_coordinates = latitude is not None and longitude is not None
        return PositionState(
            received_at=datetime.now(),
            latitude_deg=float(latitude) if latitude is not None else None,
            longitude_deg=float(longitude) if longitude is not None else None,
            altitude_m=float(altitude) if altitude is not None else None,
            speed_mps=float(speed) if speed is not None else None,
            course_deg=float(bearing) if bearing is not None else None,
            fix_mode=3 if has_coordinates and altitude is not None else (2 if has_coordinates else 1),
            accuracy_m=float(accuracy) if accuracy is not None else None,
            source="termux-location",
        )
