# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Owned controller dependencies for the Car TUI application."""

from dataclasses import dataclass

from controllers.automotive import VehicleStateSourceIf
from controllers.navigation import NavigationControllerIf
from apps.carTui.radio_catalog import CarTuiRadio


@dataclass(frozen=True, slots=True)
class CarTuiDependencies:
    """Controllers constructed by the Car TUI bootstrap."""

    navigation_controller: NavigationControllerIf
    vehicle_manager: VehicleStateSourceIf
    radios: tuple[CarTuiRadio, ...]

    def close(self) -> None:
        """Release both controller stacks safely."""
        try:
            self.navigation_controller.stop()
        finally:
            try:
                self.vehicle_manager.disconnect()
            finally:
                for radio in self.radios:
                    radio.controller.stop()
