# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-neutral route values shared by navigation UI request contracts."""

from enum import Enum, auto


class RouteTurn(str, Enum):
    """Provider-neutral maneuver direction for visual guidance."""

    UNKNOWN = "unknown"
    STRAIGHT = "straight"
    LEFT = "left"
    RIGHT = "right"
    U_TURN = "u_turn"
    ROUNDABOUT = "roundabout"
    ARRIVE = "arrive"


class TravelMode(Enum):
    """Identify the route costing mode requested by the user."""

    AUTO = auto()
    BICYCLE = auto()
    PEDESTRIAN = auto()
    TRANSIT = auto()
