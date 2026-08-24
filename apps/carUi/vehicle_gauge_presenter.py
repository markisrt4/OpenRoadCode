# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Headless application state for CarUI vehicle gauges."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from messaging.contracts.automotive import VehicleStateMessage


@dataclass(frozen=True, slots=True)
class VehicleGaugeSnapshot:
    """Immutable state rendered by the Tk vehicle-gauge screen."""

    vehicle: VehicleStateMessage | None
    error: str | None
    received_count: int

    @property
    def status(self) -> str:
        if self.error is not None:
            return self.error
        if self.vehicle is None:
            return "Waiting for vehicle telemetry"
        return (
            f"Vehicle telemetry: {self.vehicle.source} · "
            f"{self.received_count} messages"
        )


class VehicleGaugePresenter:
    """Own vehicle-gauge application state without depending on Tkinter."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._vehicle: VehicleStateMessage | None = None
        self._error: str | None = None
        self._received_count = 0

    def set_vehicle_message(self, message: VehicleStateMessage) -> None:
        with self._lock:
            self._vehicle = message
            self._error = None
            self._received_count += 1

    def set_vehicle_error(self, topic: str, error: Exception) -> None:
        with self._lock:
            self._error = (
                f"Vehicle telemetry error: {topic}: "
                f"{type(error).__name__}: {error}"
            )

    def snapshot(self) -> VehicleGaugeSnapshot:
        with self._lock:
            return VehicleGaugeSnapshot(
                vehicle=self._vehicle,
                error=self._error,
                received_count=self._received_count,
            )
