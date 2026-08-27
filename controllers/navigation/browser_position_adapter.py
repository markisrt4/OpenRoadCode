# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Normalize browser geolocation payloads for position consumers."""

from __future__ import annotations

import math
from typing import Any

from controllers.navigation.navigation_state import PositionState


class BrowserPositionAdapter:
    """Translate browser geolocation payloads into geographic position state."""

    @staticmethod
    def state_from_payload(payload: Any) -> PositionState:
        if not isinstance(payload, dict):
            raise ValueError("position must be a JSON object")

        latitude = _number(payload.get("latitude"), "latitude", required=True)
        longitude = _number(payload.get("longitude"), "longitude", required=True)
        assert latitude is not None and longitude is not None

        if not -90.0 <= latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90")
        if not -180.0 <= longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180")

        return PositionState(
            latitude_deg=latitude,
            longitude_deg=longitude,
            altitude_m=_number(payload.get("altitude"), "altitude"),
            accuracy_m=_number(payload.get("accuracy"), "accuracy"),
            fix_mode=3,
            source="browser",
        )


def _number(value: Any, name: str, *, required: bool = False) -> float | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result
