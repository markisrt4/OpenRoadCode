# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Navigation and off-road destination for Car TUI."""

from controllers.navigation import NavigationControllerIf
from frontends.tui.automotive import NavigationDashboardView


class NavigationScreen:
    """Run visibility-scoped navigation interaction in a curses window."""

    def __init__(
        self,
        controller: NavigationControllerIf,
        *,
        refresh_seconds: float = 0.1,
        gps_enabled: bool = False,
    ) -> None:
        self._controller = controller
        self._refresh_seconds = refresh_seconds
        self._gps_enabled = gps_enabled
        self._view = NavigationDashboardView()

    def run(self, window) -> bool:
        """Run until back or quit; return False when the app should quit."""
        state = None
        connected = False
        status = "Starting navigation..."
        acceleration_mode = "both"
        window.timeout(max(1, int(self._refresh_seconds * 1000)))
        try:
            try:
                self._controller.start()
                connected = True
                status = "Live navigation data"
            except Exception:
                status = "Motion sensor unavailable"
            while True:
                controls = "b/Esc: back   q: quit   h: reset   c: calibrate   a: acceleration"
                self._view.render(
                    window, state, status, connected, self._gps_enabled,
                    acceleration_mode, controls,
                )
                key = window.getch()
                if key in (ord("q"), ord("Q")):
                    return False
                if key in (ord("b"), ord("B"), 27):
                    return True
                if key in (ord("a"), ord("A")):
                    modes = ("raw", "linear", "both")
                    acceleration_mode = modes[(modes.index(acceleration_mode) + 1) % len(modes)]
                elif key in (ord("h"), ord("H")) and connected:
                    self._controller.reset_heading()
                    status = "Relative heading reset"
                elif key in (ord("c"), ord("C")) and connected:
                    status = "Calibrating; keep vehicle still..."
                    self._view.render(
                        window, state, status, connected, self._gps_enabled,
                        acceleration_mode, controls,
                    )
                    try:
                        result = self._controller.calibrate_stationary()
                        status = f"Calibrated from {result.sample_count} samples"
                    except Exception:
                        status = "Calibration failed"
                elif key in (ord("r"), ord("R")) and not connected:
                    try:
                        self._controller.start()
                        connected = True
                        status = "Live navigation data"
                    except Exception:
                        status = "Motion sensor unavailable"
                if connected:
                    try:
                        state = self._controller.read_state()
                        status = "Live navigation data"
                    except Exception:
                        connected = False
                        status = "Navigation data unavailable"
        finally:
            window.timeout(-1)
            self._controller.stop()
