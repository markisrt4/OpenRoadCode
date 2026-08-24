# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Message-bus vehicle telemetry destination for Car TUI."""

from apps.carTui.unit_preferences import CarTuiUnitPreferences
from common.telemetry.vehicle_bus_state import VehicleBusState
from frontends.tui.automotive import VehicleDashboardView


class VehicleScreen:
    """Render the latest shared vehicle telemetry until back or quit."""

    def __init__(
        self,
        vehicle_state: VehicleBusState,
        *,
        refresh_seconds: float = 0.5,
        unit_preferences: CarTuiUnitPreferences | None = None,
    ) -> None:
        self._vehicle_state = vehicle_state
        self._refresh_seconds = refresh_seconds
        self._unit_preferences = unit_preferences or CarTuiUnitPreferences()

    def run(self, window) -> bool:
        """Run until back or quit; return False when the app should quit."""
        window.timeout(max(1, int(self._refresh_seconds * 1000)))
        try:
            while True:
                snapshot = self._vehicle_state.snapshot()
                controls = "b/Esc: back   q: quit   u: units"
                view = VehicleDashboardView(self._unit_preferences.unit_system)
                view.render(window, snapshot.state, snapshot.status, snapshot.connected, controls)
                key = window.getch()
                if key in (ord("q"), ord("Q")):
                    return False
                if key in (ord("b"), ord("B"), 27):
                    return True
                if key in (ord("u"), ord("U")):
                    self._unit_preferences.toggle()
        finally:
            window.timeout(-1)
