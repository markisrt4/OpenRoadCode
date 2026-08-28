# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation state for navigation telemetry in orcUi."""

from __future__ import annotations

import math
from dataclasses import dataclass

from messaging.contracts.navigation import AttitudeStateData, PositionStateData

FEET_PER_METER = 3.280839895013123


@dataclass(frozen=True, slots=True)
class PositionPresentationState:
    """Position values ready for display by the ORC UI."""

    latitude_deg: float | None = None
    longitude_deg: float | None = None
    altitude_ft: float | None = None
    fix_mode: int | None = None
    satellites_visible: int | None = None
    satellites_used: int | None = None
    accuracy_m: float | None = None
    is_cached: bool = False


@dataclass(frozen=True, slots=True)
class AttitudePresentationState:
    """Vehicle orientation values ready for display by the ORC UI."""

    heading_deg: float | None = None
    pitch_deg: float | None = None
    roll_deg: float | None = None


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

    @staticmethod
    def present_attitude(state: AttitudeStateData) -> AttitudePresentationState:
        return AttitudePresentationState(
            heading_deg=(
                math.degrees(state.heading_rad) % 360.0
                if state.heading_rad is not None
                else None
            ),
            pitch_deg=(
                math.degrees(state.pitch_rad)
                if state.pitch_rad is not None
                else None
            ),
            roll_deg=(
                math.degrees(state.roll_rad)
                if state.roll_rad is not None
                else None
            ),
        )
