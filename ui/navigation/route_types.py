# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-neutral route values shared by navigation UI request contracts."""

from enum import Enum, auto


class TravelMode(Enum):
    """Identify the route costing mode requested by the user."""

    AUTO = auto()
    BICYCLE = auto()
    PEDESTRIAN = auto()
    TRANSIT = auto()
