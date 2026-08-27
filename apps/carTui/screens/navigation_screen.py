# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation and off-road destination for Car TUI."""

from apps.carTui.unit_preferences import CarTuiUnitPreferences
from common.telemetry.navigation_bus_state import NavigationBusState
from frontends.tui.automotive import NavigationDashboardView


class NavigationScreen:
    """Render navigation telemetry supplied by the shared message bus."""

    def __init__(
        self,
        state: NavigationBusState,
        *,
        refresh_seconds: float = 0.1,
        gps_enabled: bool = False,
        unit_preferences: CarTuiUnitPreferences | None = None,
    ) -> None:
        self._state = state
        self._refresh_seconds = refresh_seconds
        self._gps_enabled = gps_enabled
        self._unit_preferences = unit_preferences or CarTuiUnitPreferences()

    def run(self, window) -> bool:
        """Run until back or quit; return False when the app should quit."""
        acceleration_mode = "both"
        window.timeout(max(1, int(self._refresh_seconds * 1000)))
        try:
            while True:
                snapshot = self._state.snapshot()
                controls = "b/Esc: back   q: quit   a: acceleration   u: units"
                view = NavigationDashboardView(self._unit_preferences.unit_system)
                view.render(
                    window,
                    snapshot if snapshot.connected else None,
                    snapshot.status,
                    snapshot.connected,
                    self._gps_enabled,
                    acceleration_mode,
                    controls,
                )
                key = window.getch()
                if key in (ord("q"), ord("Q")):
                    return False
                if key in (ord("b"), ord("B"), 27):
                    return True
                if key in (ord("a"), ord("A")):
                    modes = ("raw", "linear", "both")
                    acceleration_mode = modes[(modes.index(acceleration_mode) + 1) % len(modes)]
                if key in (ord("u"), ord("U")):
                    self._unit_preferences.toggle()
        finally:
            window.timeout(-1)
