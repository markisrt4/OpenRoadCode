# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own a vehicle-state source and publish automotive telemetry."""

from __future__ import annotations

from dataclasses import replace
import threading
import time

from controllers.automotive.gear_estimator import GearEstimator
from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf
from messaging.contracts.automotive import VehicleStatePublisher
from protocols.obd2 import Obd2Error


class AutomotiveRuntime:
    """Publish complete vehicle-state snapshots at a configured rate."""

    def __init__(
        self,
        source: VehicleStateSourceIf,
        publisher,
        *,
        publish_source: str = "automotive-service",
        rate_hz: float = 10.0,
        reconnect_interval_s: float = 2.0,
        gear_estimator: GearEstimator | None = None,
    ) -> None:
        if rate_hz <= 0.0:
            raise ValueError("rate_hz must be greater than zero")
        if reconnect_interval_s <= 0.0:
            raise ValueError("reconnect_interval_s must be greater than zero")
        self._source = source
        self._state_publisher = VehicleStatePublisher(publisher, source=publish_source)
        self._period_s = 1.0 / rate_hz
        self._reconnect_interval_s = reconnect_interval_s
        self._gear_estimator = gear_estimator
        self._stop_event = threading.Event()
        self._connected = False

    def start(self) -> None:
        """Prepare the runtime; source connection is managed by run()."""
        self._stop_event.clear()

    def run(self) -> None:
        """Publish snapshots and reconnect the source after OBD-II failures."""
        self.start()
        try:
            while not self._stop_event.is_set():
                if not self._connected:
                    if not self._try_connect():
                        self._stop_event.wait(self._reconnect_interval_s)
                        continue

                started = time.monotonic()
                try:
                    state = self._source.read_state()
                except Obd2Error:
                    self._disconnect_source()
                    self._stop_event.wait(self._reconnect_interval_s)
                    continue

                if self._gear_estimator is not None:
                    state = replace(
                        state,
                        transmission_gear=self._gear_estimator.estimate(
                            state.engine_speed_rad_s,
                            state.vehicle_speed_m_s,
                        ),
                    )
                self._state_publisher.publish(state)
                remaining = self._period_s - (time.monotonic() - started)
                if remaining > 0.0:
                    self._stop_event.wait(remaining)
        finally:
            self.close()

    def close(self) -> None:
        """Stop publishing and disconnect the owned source."""
        self._stop_event.set()
        self._disconnect_source()

    def _try_connect(self) -> bool:
        try:
            self._source.connect()
        except Obd2Error:
            self._disconnect_source()
            return False
        self._connected = True
        return True

    def _disconnect_source(self) -> None:
        if not self._connected:
            return
        try:
            self._source.disconnect()
        finally:
            self._connected = False
