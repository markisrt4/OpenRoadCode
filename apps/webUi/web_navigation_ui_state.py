# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Thread-safe navigation state consumed by the WebUI backend."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock

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
        self._lock = Lock()
        self._position: PositionStateMessage | None = None
        self._motion: MotionStateMessage | None = None
        self._error: str | None = None

    def set_position(self, message: PositionStateMessage) -> None:
        with self._lock:
            self._position = message
            self._error = None

    def set_motion(self, message: MotionStateMessage) -> None:
        with self._lock:
            self._motion = message
            self._error = None

    def set_error(self, topic: str, error: Exception) -> None:
        with self._lock:
            self._error = f"{topic}: {error}"

    def snapshot(self) -> WebNavigationSnapshot:
        with self._lock:
            return WebNavigationSnapshot(
                position=self._position,
                motion=self._motion,
                error=self._error,
            )

    def as_dict(self) -> dict[str, object]:
        return self.snapshot().as_dict()
