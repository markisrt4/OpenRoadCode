# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable Tk automotive screens and panels."""

from frontends.tk.automotive.fuel_level_gauge import FuelLevelGauge
from frontends.tk.automotive.offroad_dashboard_panel import OffroadDashboardPanel
from frontends.tk.automotive.shifter_gauge import ShifterGauge, ShifterTheme
from frontends.tk.automotive.vehicle_gauge_panel import (
    DEFAULT_GAUGES,
    GaugeDefinition,
    VehicleGaugeSnapshot,
    VehicleGaugePanel,
)

__all__ = [
    "DEFAULT_GAUGES",
    "FuelLevelGauge",
    "GaugeDefinition",
    "OffroadDashboardPanel",
    "ShifterGauge",
    "ShifterTheme",
    "VehicleGaugePanel",
    "VehicleGaugeSnapshot",
]
