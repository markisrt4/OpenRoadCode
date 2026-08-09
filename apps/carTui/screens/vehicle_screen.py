"""OBD-II vehicle telemetry destination for Car TUI."""

from controllers.automotive import VehicleStateSourceIf
from frontends.tui.automotive import VehicleDashboardView
from protocols.obd2 import Obd2ConnectionError, Obd2Error


class VehicleScreen:
    """Run visibility-scoped OBD-II interaction in a curses window."""

    def __init__(
        self,
        manager: VehicleStateSourceIf,
        *,
        refresh_seconds: float = 0.5,
    ) -> None:
        self._manager = manager
        self._refresh_seconds = refresh_seconds
        self._view = VehicleDashboardView()

    def run(self, window) -> bool:
        """Run until back or quit; return False when the app should quit."""
        state = None
        connected = False
        status = "Starting vehicle connection..."
        window.timeout(max(1, int(self._refresh_seconds * 1000)))
        try:
            try:
                self._manager.connect()
                connected = True
                status = "Live vehicle data"
            except Obd2ConnectionError:
                status = "Vehicle connection unavailable"
            while True:
                controls = "b/Esc: back   q: quit   r: reconnect"
                self._view.render(window, state, status, connected, controls)
                key = window.getch()
                if key in (ord("q"), ord("Q")):
                    return False
                if key in (ord("b"), ord("B"), 27):
                    return True
                if key in (ord("r"), ord("R")) and not connected:
                    try:
                        self._manager.connect()
                        connected = True
                    except Obd2ConnectionError:
                        status = "Vehicle connection unavailable"
                if connected:
                    try:
                        state = self._manager.read_state()
                        status = "Live vehicle data"
                    except Obd2ConnectionError:
                        connected = False
                        status = "Vehicle connection lost"
                    except Obd2Error:
                        status = "Vehicle telemetry warning"
        finally:
            window.timeout(-1)
            self._manager.disconnect()
