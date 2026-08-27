# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Thread-safe navigation state consumed by the WebUI backend."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Condition

from messaging.contracts.navigation import MotionStateMessage, PositionStateMessage


@dataclass(frozen=True, slots=True)
class WebNavigationSnapshot:
    """Immutable snapshot of the latest navigation bus messages."""

    position: PositionStateMessage | None
    motion: MotionStateMessage | None
    error: str | None

    def as_dict(self) -> dict[str, object]:
        """Return contract-shaped JSON-compatible data for Flask."""
        return {
            "position": None if self.position is None else asdict(self.position),
            "motion": None if self.motion is None else asdict(self.motion),
            "error": self.error,
        }


class WebNavigationUiState:
    """Store the latest decoded navigation messages for HTTP consumers."""

    def __init__(self) -> None:
        self._condition = Condition()
        self._position: PositionStateMessage | None = None
        self._motion: MotionStateMessage | None = None
        self._error: str | None = None
        self._generation = 0

    def set_position(self, message: PositionStateMessage) -> None:
        with self._condition:
            self._position = message
            self._error = None
            self._changed()

    def set_motion(self, message: MotionStateMessage) -> None:
        with self._condition:
            self._motion = message
            self._error = None
            self._changed()

    def set_error(self, topic: str, error: Exception) -> None:
        with self._condition:
            self._error = f"{topic}: {error}"
            self._changed()

    def snapshot(self) -> WebNavigationSnapshot:
        with self._condition:
            return self._snapshot_unlocked()

    def versioned_snapshot(self) -> tuple[int, WebNavigationSnapshot]:
        """Return the current change generation with an immutable snapshot."""
        with self._condition:
            return self._generation, self._snapshot_unlocked()

    def wait_for_update(
        self,
        after_generation: int,
        *,
        timeout_s: float = 15.0,
    ) -> tuple[int, WebNavigationSnapshot] | None:
        """Wait until state changes; return None on heartbeat timeout."""
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

    def _snapshot_unlocked(self) -> WebNavigationSnapshot:
        return WebNavigationSnapshot(
            position=self._position,
            motion=self._motion,
            error=self._error,
        )
