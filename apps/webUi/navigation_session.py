# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-owned state for browser navigation sensor reports."""

from __future__ import annotations

from dataclasses import asdict
from threading import Lock
from typing import Any

from controllers.navigation.browser_orientation_adapter import BrowserOrientationAdapter
from controllers.navigation.browser_position_adapter import BrowserPositionAdapter
from controllers.navigation.navigation_state import OrientationState, PositionState


class WebNavigationSession:
    """Store the latest normalized navigation reports received by WebUi."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._position: PositionState | None = None
        self._orientation: OrientationState | None = None

    def update_position(self, payload: Any) -> PositionState:
        state = BrowserPositionAdapter.state_from_payload(payload)
        with self._lock:
            self._position = state
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
