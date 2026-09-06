# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Position source backed by the OpenRoadCode Android sensor bridge."""

from __future__ import annotations

from threading import Event, Thread

from controllers.navigation.navigation_state import PositionState
from controllers.navigation.position_source_if import PositionStateCallback, PositionSourceIf
from hardware_io.android.sensor_bridge_client import AndroidSensorBridgeClient


class AndroidPositionSource(PositionSourceIf):
    """Poll Android's fused location snapshot through the local bridge."""

    def __init__(self, client: AndroidSensorBridgeClient, *, poll_interval_s: float = 0.5) -> None:
        self._client = client
        self._poll_interval_s = poll_interval_s
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self, callback: PositionStateCallback) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(
            target=self._run,
            args=(callback,),
            name="android-position-source",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None

    def _run(self, callback: PositionStateCallback) -> None:
        last_timestamp_ms: int | None = None
        while not self._stop_event.is_set():
            try:
                sample = self._client.read_location()
                if sample.timestamp_ms != last_timestamp_ms:
                    callback(PositionState(
                        latitude_deg=sample.latitude_deg,
                        longitude_deg=sample.longitude_deg,
                        altitude_m=sample.altitude_m,
                        speed_mps=sample.speed_mps,
                        course_deg=sample.bearing_deg,
                        fix_mode=3,
                        accuracy_m=sample.horizontal_accuracy_m,
                        source=f"android-{sample.provider}",
                    ))
                    last_timestamp_ms = sample.timestamp_ms
            except RuntimeError:
                # The bridge may legitimately be starting or waiting for its
                # first Android location fix. Keep the navigation service alive.
                pass
            self._stop_event.wait(self._poll_interval_s)
