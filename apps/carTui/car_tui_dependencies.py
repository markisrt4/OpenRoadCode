# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Owned runtime dependencies for the Car TUI application."""

from dataclasses import dataclass

from apps.carTui.navigation_bus_state import NavigationBusState
from apps.carTui.radio_catalog import CarTuiRadio
from apps.carTui.vehicle_bus_state import VehicleBusState
from messaging.message_dispatcher import MessageDispatcher


@dataclass(frozen=True, slots=True)
class CarTuiDependencies:
    """Shared bus consumers and remaining direct radio controllers."""

    navigation_state: NavigationBusState
    vehicle_state: VehicleBusState
    telemetry_dispatcher: MessageDispatcher
    radios: tuple[CarTuiRadio, ...]

    def close(self) -> None:
        """Release message-bus and radio resources safely."""
        try:
            self.telemetry_dispatcher.close()
        finally:
            for radio in self.radios:
                radio.controller.stop()
