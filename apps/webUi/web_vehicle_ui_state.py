# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Thread-safe vehicle state consumed by the WebUI backend."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Condition

from messaging.contracts.automotive import VehicleStateMessage


@dataclass(frozen=True, slots=True)
class WebVehicleSnapshot:
    """Immutable snapshot of the latest vehicle-state message."""

    vehicle: VehicleStateMessage | None
    error: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "vehicle": None if self.vehicle is None else asdict(self.vehicle),
            "error": self.error,
        }


class WebVehicleUiState:
    """Store the latest decoded automotive message for HTTP/SSE consumers."""

    def __init__(self) -> None:
        self._condition = Condition()
        self._vehicle: VehicleStateMessage | None = None
        self._error: str | None = None
        self._generation = 0

    def set_vehicle(self, message: VehicleStateMessage) -> None:
        with self._condition:
            self._vehicle = message
            self._error = None
            self._changed()

    def set_error(self, topic: str, error: Exception) -> None:
        with self._condition:
            self._error = f"{topic}: {error}"
            self._changed()

    def snapshot(self) -> WebVehicleSnapshot:
        with self._condition:
            return self._snapshot_unlocked()

    def versioned_snapshot(self) -> tuple[int, WebVehicleSnapshot]:
        with self._condition:
            return self._generation, self._snapshot_unlocked()

    def wait_for_update(
        self,
        after_generation: int,
        *,
        timeout_s: float = 15.0,
    ) -> tuple[int, WebVehicleSnapshot] | None:
        with self._condition:
            changed = self._condition.wait_for(
                lambda: self._generation != after_generation,
                timeout=timeout_s,
            )
            if not changed:
                return None
            return self._generation, self._snapshot_unlocked()

    def as_dict(self) -> dict[str, object]:
        return self.snapshot().as_dict()

    def _changed(self) -> None:
        self._generation += 1
        self._condition.notify_all()

    def _snapshot_unlocked(self) -> WebVehicleSnapshot:
        return WebVehicleSnapshot(vehicle=self._vehicle, error=self._error)
