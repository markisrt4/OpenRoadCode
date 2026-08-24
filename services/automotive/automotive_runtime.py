# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own a vehicle-state source and publish automotive telemetry."""

from __future__ import annotations

import threading
import time

from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf
from messaging.contracts.automotive import VehicleStatePublisher


class AutomotiveRuntime:
    """Publish complete vehicle-state snapshots at a configured rate."""

    def __init__(
        self,
        source: VehicleStateSourceIf,
        publisher,
        *,
        publish_source: str = "automotive-service",
        rate_hz: float = 10.0,
    ) -> None:
        if rate_hz <= 0.0:
            raise ValueError("rate_hz must be greater than zero")
        self._source = source
        self._state_publisher = VehicleStatePublisher(publisher, source=publish_source)
        self._period_s = 1.0 / rate_hz
        self._stop_event = threading.Event()
        self._connected = False

    def start(self) -> None:
        """Connect the configured vehicle-state source."""
        self._source.connect()
        self._connected = True
        self._stop_event.clear()

    def run(self) -> None:
        """Publish source snapshots until close() is called."""
        self.start()
        try:
            while not self._stop_event.is_set():
                started = time.monotonic()
                self._state_publisher.publish(self._source.read_state())
                remaining = self._period_s - (time.monotonic() - started)
                if remaining > 0.0:
                    self._stop_event.wait(remaining)
        finally:
            self.close()

    def close(self) -> None:
        """Stop publishing and disconnect the owned source."""
        self._stop_event.set()
        if self._connected:
            self._source.disconnect()
            self._connected = False
