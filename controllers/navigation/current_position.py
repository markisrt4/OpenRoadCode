# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Process-local latest navigation position shared by UI-independent consumers."""

from __future__ import annotations

from threading import Lock

from ui.navigation import GeoPoint

_lock = Lock()
_current_position: GeoPoint | None = None


def set_current_position(position: GeoPoint | None) -> None:
    """Replace the latest known process-local navigation position."""
    global _current_position
    with _lock:
        _current_position = position


def get_current_position() -> GeoPoint | None:
    """Return the latest process-local navigation position, if available."""
    with _lock:
        return _current_position
