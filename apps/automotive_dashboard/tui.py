from __future__ import annotations

import argparse
import curses
import time

from controllers.automotive import VehicleState
from controllers.automotive.obd2 import Elm327ObdAdapter, Obd2Manager
from hardware_io.automotive.elm327 import Elm327Device
from protocols.obd2 import Obd2ConnectionError, Obd2Error


def _format(value: float | int | None, unit: str, precision: int = 1) -> str:
    if value is None:
        return "--"
    if isinstance(value, int):
        return f"{value} {unit}".strip()
    return f"{value:.{precision}f} {unit}".strip()


def _fields(state: VehicleState | None) -> tuple[tuple[str, str], ...]:
    if state is None:
        return tuple((label, "--") for label in (
            "Engine RPM", "Vehicle speed", "Boost", "Coolant",
            "Intake air", "Throttle", "Accelerator", "Engine load",
            "MAP", "Barometric", "Mass airflow", "Fuel level",
            "Module voltage",
        ))

    return (
        ("Engine RPM", _format(state.rpm, "rpm", 0)),
        ("Vehicle speed", _format(state.speed_mph, "mph")),
        ("Boost", _format(state.boost_psi, "psi")),
        ("Coolant", _format(state.coolant_temp_f, "°F")),
        ("Intake air", _format(state.intake_temp_f, "°F")),
        ("Throttle", _format(state.throttle_pct, "%")),
        ("Accelerator", _format(state.accelerator_pedal_pct, "%")),
        ("Engine load", _format(state.engine_load_pct, "%")),
        ("MAP", _format(state.map_kpa, "kPa")),
        ("Barometric", _format(state.baro_kpa, "kPa")),
        ("Mass airflow", _format(state.maf_gps, "g/s", 2)),
        ("Fuel level", _format(state.fuel_level_pct, "%")),
        ("Module voltage", _format(state.control_voltage, "V", 2)),
    )


def _addstr(
    screen: curses.window,
    row: int,
    column: int,
    text: str,
    attributes: int = 0,
) -> None:
    height, width = screen.getmaxyx()
    if row < 0 or row >= height or column < 0 or column >= width:
        return
    try:
        screen.addnstr(row, column, text, width - column - 1, attributes)
    except curses.error:
        pass


def _render(
    screen: curses.window,
    state: VehicleState | None,
    status: str,
    connected: bool,
) -> None:
    screen.erase()
    height, width = screen.getmaxyx()

    title_attr = curses.A_BOLD
    if curses.has_colors():
        title_attr |= curses.color_pair(1)
    _addstr(screen, 0, 2, "OpenRoadCode Vehicle State", title_attr)
    _addstr(screen, 1, 0, "─" * max(0, width - 1))

    connection = "CONNECTED" if connected else "DISCONNECTED"
    connection_attr = curses.A_BOLD
    if curses.has_colors():
        connection_attr |= curses.color_pair(2 if connected else 3)
    _addstr(screen, 2, 2, connection, connection_attr)

    if state is not None:
        _addstr(
            screen,
            2,
            max(24, width - 24),
            f"Updated {state.timestamp:%H:%M:%S}",
        )

    fields = _fields(state)
    two_columns = width >= 72
    rows_per_column = (len(fields) + 1) // 2 if two_columns else len(fields)
    column_width = width // 2 if two_columns else width

    for index, (label, value) in enumerate(fields):
        column_index = index // rows_per_column if two_columns else 0
        row_index = index % rows_per_column if two_columns else index
        row = 4 + row_index
        column = 2 + column_index * column_width
        _addstr(screen, row, column, f"{label:<16}", curses.A_DIM)
        _addstr(screen, row, column + 17, value, curses.A_BOLD)

    footer_row = min(height - 2, 5 + rows_per_column)
    _addstr(screen, footer_row, 0, "─" * max(0, width - 1))
    _addstr(screen, footer_row + 1, 2, status)
    controls = "q: quit"
    if not connected:
        controls += "   r: reconnect"
    _addstr(screen, height - 1, max(2, width - len(controls) - 2), controls)
    screen.refresh()


def _wait_for_key(screen: curses.window, seconds: float) -> int:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        key = screen.getch()
        if key != -1:
            return key
        time.sleep(0.05)
    return -1


def _run(
    screen: curses.window,
    manager: Obd2Manager,
    refresh_seconds: float,
) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.nodelay(True)

    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)

    state: VehicleState | None = None
    connected = False
    status = "Starting..."

    while True:
        key = screen.getch()
        if key in (ord("q"), ord("Q")):
            return

        if not connected:
            try:
                status = "Connecting to ELM327..."
                _render(screen, state, status, connected)
                manager.connect()
                connected = True
                status = "Connected; polling vehicle state"
            except Obd2ConnectionError as exc:
                status = f"Connection error: {exc}"

            _render(screen, state, status, connected)
            if not connected:
                while True:
                    key = _wait_for_key(screen, 0.1)
                    if key in (ord("q"), ord("Q")):
                        return
                    if key in (ord("r"), ord("R")):
                        break
                continue

        try:
            status = "Polling vehicle ECUs..."
            _render(screen, state, status, connected)
            state = manager.read_state()
            status = "Live data; unsupported values are shown as --"
        except Obd2ConnectionError as exc:
            connected = False
            status = f"Connection lost: {exc}"
        except Obd2Error as exc:
            status = f"OBD-II warning: {exc}"

        _render(screen, state, status, connected)
        key = _wait_for_key(screen, refresh_seconds)
        if key in (ord("q"), ord("Q")):
            return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display live OBD-II vehicle state in a terminal dashboard."
    )
    parser.add_argument("--port", default="/dev/rfcomm0")
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument(
        "--refresh",
        type=float,
        default=0.5,
        help="Delay in seconds between complete vehicle-state polls",
    )
    parser.add_argument(
        "--slow-refresh",
        type=float,
        default=5.0,
        help="Seconds between polls of temperatures, fuel, and other slow data",
    )
    args = parser.parse_args()
    if args.refresh < 0:
        parser.error("--refresh must be zero or greater")
    if args.slow_refresh <= 0:
        parser.error("--slow-refresh must be greater than zero")
    return args


def main() -> int:
    args = parse_args()
    device = Elm327Device(port=args.port, baud=args.baud)
    manager = Obd2Manager(
        Elm327ObdAdapter(device),
        slow_poll_interval_seconds=args.slow_refresh,
    )

    try:
        curses.wrapper(_run, manager, args.refresh)
    finally:
        manager.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
