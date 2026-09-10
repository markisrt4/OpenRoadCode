# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation model for automotive trip telemetry shown by orcUi."""

from __future__ import annotations

from dataclasses import dataclass

from messaging.contracts.automotive import TripStateData

MILES_PER_METRE = 0.000621371192237334
MPH_PER_MPS = 2.2369362920544
GALLONS_PER_CUBIC_METRE = 264.1720523581484


@dataclass(frozen=True, slots=True)
class TripPresentationState:
    """Trip telemetry converted into driver-facing units."""

    status: str = "idle"
    distance_miles: float = 0.0
    elapsed_s: float = 0.0
    moving_s: float = 0.0
    stopped_s: float = 0.0
    average_speed_mph: float | None = None
    maximum_speed_mph: float | None = None
    fuel_used_gallons: float | None = None
    economy_mpg: float | None = None
    estimated_range_miles: float | None = None


class TripPresenter:
    """Convert the SI-normalized trip contract for cockpit display."""

    @staticmethod
    def present(state: TripStateData) -> TripPresentationState:
        economy_mpg = None
        if (
            state.average_fuel_consumption_m3_per_m is not None
            and state.average_fuel_consumption_m3_per_m > 0.0
        ):
            gallons_per_mile = (
                state.average_fuel_consumption_m3_per_m
                * GALLONS_PER_CUBIC_METRE
                / MILES_PER_METRE
            )
            if gallons_per_mile > 0.0:
                economy_mpg = 1.0 / gallons_per_mile

        return TripPresentationState(
            status=state.status,
            distance_miles=state.distance_m * MILES_PER_METRE,
            elapsed_s=state.elapsed_s,
            moving_s=state.moving_s,
            stopped_s=state.stopped_s,
            average_speed_mph=(
                None
                if state.average_speed_m_s is None
                else state.average_speed_m_s * MPH_PER_MPS
            ),
            maximum_speed_mph=(
                None
                if state.maximum_speed_m_s is None
                else state.maximum_speed_m_s * MPH_PER_MPS
            ),
            fuel_used_gallons=(
                None
                if state.fuel_used_m3 is None
                else state.fuel_used_m3 * GALLONS_PER_CUBIC_METRE
            ),
            economy_mpg=economy_mpg,
            estimated_range_miles=(
                None
                if state.estimated_range_m is None
                else state.estimated_range_m * MILES_PER_METRE
            ),
        )
