# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Mutable presentation preferences owned by the Car TUI."""

from dataclasses import dataclass

from common.units import UnitSystem


@dataclass(slots=True)
class CarTuiUnitPreferences:
    """Hold the currently selected presentation unit system."""

    unit_system: UnitSystem = UnitSystem.IMPERIAL

    def toggle(self) -> UnitSystem:
        """Switch between imperial and metric presentation units."""
        self.unit_system = (
            UnitSystem.METRIC
            if self.unit_system == UnitSystem.IMPERIAL
            else UnitSystem.IMPERIAL
        )
        return self.unit_system
