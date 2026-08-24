# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-owned state for browser navigation sensor reports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from threading import Lock
from typing import Any

from controllers.navigation.browser_orientation_adapter import BrowserOrientationAdapter
from controllers.navigation.browser_position_adapter import BrowserPositionAdapter
from controllers.navigation.navigation_state import OrientationState, PositionState


PositionStateSink = Callable[[PositionState], None]


class WebNavigationSession:
    """Store normalized browser navigation reports and optionally forward fixes."""

    def __init__(self, *, position_sink: PositionStateSink | None = None) -> None:
        self._lock = Lock()
        self._position: PositionState | None = None
        self._orientation: OrientationState | None = None
        self._position_sink = position_sink

    def update_position(self, payload: Any) -> PositionState:
        """Normalize one browser geolocation report and forward the state."""
        state = BrowserPositionAdapter.state_from_payload(payload)
        with self._lock:
            self._position = state

        if self._position_sink is not None:
            self._position_sink(state)

        return state

    def update_orientation(self, payload: Any) -> OrientationState:
        state = BrowserOrientationAdapter.state_from_payload(payload)
        with self._lock:
            self._orientation = state
        return state

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            position = self._position
            orientation = self._orientation
        return {
            "position": asdict(position) if position is not None else None,
            "orientation": asdict(orientation) if orientation is not None else None,
        }
