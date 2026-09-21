# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Present ORC navigation state on the reusable off-road dashboard."""

from __future__ import annotations

import math

from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from frontends.tk.automotive import OffroadDashboardPanel
from ui.navigation import HeadingReference, PositionFix


def apply_offroad_dashboard_state(
    panel: OffroadDashboardPanel,
    *,
    position: PositionPresentationState,
    attitude: AttitudePresentationState,
) -> None:
    """Apply presentation-friendly navigation state to an off-road dashboard."""
    panel.set_heading(
        None if attitude.heading_deg is None else math.radians(attitude.heading_deg),
        HeadingReference.RELATIVE,
    )
    panel.set_pitch(
        None if attitude.pitch_deg is None else math.radians(attitude.pitch_deg)
    )
    panel.set_roll(
        None if attitude.roll_deg is None else math.radians(attitude.roll_deg)
    )

    if position.latitude_deg is None or position.longitude_deg is None:
        panel.set_position(None)
        return

    panel.set_position(
        PositionFix(
            latitude_rad=math.radians(position.latitude_deg),
            longitude_rad=math.radians(position.longitude_deg),
            altitude_m=(
                None
                if position.altitude_ft is None
                else position.altitude_ft / 3.280839895013123
            ),
            pfom_m=position.accuracy_m,
        )
    )
