# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Owned runtime dependencies for the Car TUI application."""

from dataclasses import dataclass

from apps.carTui.radio_catalog import CarTuiRadio
from apps.carTui.vehicle_bus_state import VehicleBusState
from controllers.navigation import NavigationControllerIf
from messaging.message_dispatcher import MessageDispatcher


@dataclass(frozen=True, slots=True)
class CarTuiDependencies:
    """Controllers and shared bus consumers constructed by Car TUI bootstrap."""

    navigation_controller: NavigationControllerIf
    vehicle_state: VehicleBusState
    vehicle_dispatcher: MessageDispatcher
    radios: tuple[CarTuiRadio, ...]

    def close(self) -> None:
        """Release controller, message-bus, and radio resources safely."""
        try:
            self.navigation_controller.stop()
        finally:
            try:
                self.vehicle_dispatcher.close()
            finally:
                for radio in self.radios:
                    radio.controller.stop()
