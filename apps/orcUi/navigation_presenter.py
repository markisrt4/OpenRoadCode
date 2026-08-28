# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation state for navigation position telemetry in orcUi."""

from __future__ import annotations

import math
from dataclasses import dataclass

from messaging.contracts.navigation import PositionStateData

FEET_PER_METER = 3.280839895013123


@dataclass(frozen=True, slots=True)
class PositionPresentationState:
    """Values ready for display by the ORC UI."""

    latitude_deg: float | None = None
    longitude_deg: float | None = None
    altitude_ft: float | None = None
    fix_mode: int | None = None
    satellites_visible: int | None = None
    satellites_used: int | None = None
    accuracy_m: float | None = None
    is_cached: bool = False


class NavigationPresenter:
    """Convert canonical SI navigation state into display-oriented values."""

    @staticmethod
    def present_position(state: PositionStateData) -> PositionPresentationState:
        return PositionPresentationState(
            latitude_deg=(
                math.degrees(state.latitude_rad)
                if state.latitude_rad is not None
                else None
            ),
            longitude_deg=(
                math.degrees(state.longitude_rad)
                if state.longitude_rad is not None
                else None
            ),
            altitude_ft=(
                state.altitude_m * FEET_PER_METER
                if state.altitude_m is not None
                else None
            ),
            fix_mode=state.fix_mode,
            satellites_visible=state.satellites_visible,
            satellites_used=state.satellites_used,
            accuracy_m=state.accuracy_m,
            is_cached=state.is_cached,
        )
