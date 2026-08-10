"""Reusable terminal automotive dashboard views."""

from frontends.tui.automotive.navigation_dashboard_view import (
    ACCELERATION_MODES,
    NavigationDashboardView,
)
from frontends.tui.automotive.vehicle_dashboard_view import VehicleDashboardView

__all__ = [
    "ACCELERATION_MODES",
    "NavigationDashboardView",
    "VehicleDashboardView",
]
