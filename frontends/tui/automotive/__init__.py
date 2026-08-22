# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable terminal automotive dashboard views."""

from frontends.tui.automotive.navigation_dashboard_view import (
    ACCELERATION_MODES,
    NavigationDashboardView,
)
from frontends.tui.automotive.unit_system import UnitSystem
from frontends.tui.automotive.vehicle_dashboard_view import VehicleDashboardView

__all__ = [
    "ACCELERATION_MODES",
    "NavigationDashboardView",
    "UnitSystem",
    "VehicleDashboardView",
]
