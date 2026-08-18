# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Normalize browser DeviceOrientation reports for navigation consumers."""

from __future__ import annotations

import math
from typing import Any

from controllers.navigation.navigation_state import OrientationState


class BrowserOrientationAdapter:
    """Translate browser orientation payloads into navigation state contracts."""

    @staticmethod
    def state_from_payload(payload: Any) -> OrientationState:
        if not isinstance(payload, dict):
            raise ValueError("orientation must be a JSON object")

        heading = _number(payload.get("heading"), "heading")
        pitch = _number(payload.get("pitch"), "pitch")
        roll = _number(payload.get("roll"), "roll")
        absolute = payload.get("absolute")

        if absolute is not None and not isinstance(absolute, bool):
            raise ValueError("absolute must be a boolean")

        if heading is not None:
            heading %= 360.0
        if pitch is not None and not -180.0 <= pitch <= 180.0:
            raise ValueError("pitch must be between -180 and 180 degrees")
        if roll is not None and not -90.0 <= roll <= 90.0:
            raise ValueError("roll must be between -90 and 90 degrees")

        return OrientationState(
            heading_deg=heading,
            pitch_deg=pitch,
            roll_deg=roll,
            absolute=absolute,
            source="browser",
        )


def _number(value: Any, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result
