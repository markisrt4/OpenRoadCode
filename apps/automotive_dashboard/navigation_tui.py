"""Terminal dashboard for live vehicle navigation state."""

from __future__ import annotations

import argparse
import curses
import math
import time

from controllers.navigation import (
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
    NavigationState,
)
from hardware_io.imu import Mpu6050Imu, Vector3


ACCELERATION_MODES = ("raw", "linear", "both")


def _format(
    value: float | int | None,
    unit: str = "",
    precision: int = 1,
) -> str:
    if value is None:
        return "--"
    if isinstance(value, int):
        return f"{value} {unit}".strip()
    return f"{value:.{precision}f} {unit}".strip()


def _fields(
    state: NavigationState | None,
    gps_enabled: bool,
    acceleration_mode: str = "both",
) -> tuple[tuple[str, str], ...]:
    if acceleration_mode not in ACCELERATION_MODES:
        raise ValueError(f"invalid acceleration mode: {acceleration_mode}")

    fields: list[tuple[str, str]] = []
    orientation_labels = [
        "Heading",
        "Pitch",
        "Roll",
    ]

    if state is None:
        fields.extend((label, "--") for label in orientation_labels)
    else:
        fields.extend((
            ("Heading", _format(state.heading_deg, "°", 2)),
            ("Pitch", _format(state.pitch_deg, "°", 2)),
            ("Roll", _format(state.roll_deg, "°", 2)),
        ))

    if acceleration_mode in ("raw", "both"):
        fields.extend(
            _acceleration_fields(
                state.acceleration_mps2 if state is not None else None,
                "Raw accel",
            )
        )
    if acceleration_mode in ("linear", "both"):
        fields.extend(
            _acceleration_fields(
                (
                    state.linear_acceleration_mps2
                    if state is not None
                    else None
                ),
                "Linear accel",
            )
        )

    angular_velocity = (
        state.angular_velocity_rad_s if state is not None else None
    )
    fields.extend(
        (
            (
                "Angular velocity X",
                _format(
                    angular_velocity.x
                    if angular_velocity is not None
                    else None,
                    "rad/s",
                    4,
                ),
            ),
            (
                "Angular velocity Y",
                _format(
                    angular_velocity.y
                    if angular_velocity is not None
                    else None,
                    "rad/s",
                    4,
                ),
            ),
            (
                "Angular velocity Z",
                _format(
                    angular_velocity.z
                    if angular_velocity is not None
                    else None,
                    "rad/s",
                    4,
                ),
            ),
        )
    )

    if not gps_enabled:
        return tuple(fields)

    gps = state.gps if state is not None else None
    fields.extend(
        (
            (
                "GPS fix",
                (
                    f"{gps.fix_mode}D"
                    if gps is not None and gps.has_fix
                    else "Waiting"
                ),
            ),
            (
                "Latitude",
                _format(
                    gps.latitude_deg if gps is not None else None,
                    "°",
                    6,
                ),
            ),
            (
                "Longitude",
                _format(
                    gps.longitude_deg if gps is not None else None,
                    "°",
                    6,
                ),
            ),
            (
                "Altitude",
                _format(
                    gps.altitude_m if gps is not None else None,
                    "m",
                    1,
                ),
            ),
            (
                "Ground speed",
                _format(
                    gps.speed_mps if gps is not None else None,
                    "m/s",
                    2,
                ),
            ),
            (
                "Course over ground",
                _format(
                    gps.course_deg if gps is not None else None,
                    "°",
                    1,
                ),
            ),
            (
                "Satellites",
                (
                    str(gps.satellites_used)
                    if gps is not None
                    and gps.satellites_used is not None
                    else "--"
                ),
            ),
        )
    )
    return tuple(fields)


def _acceleration_fields(
    acceleration: Vector3 | None,
    label_prefix: str,
) -> tuple[tuple[str, str], ...]:
    if acceleration is None:
        return tuple(
            (f"{label_prefix} {axis}", "--")
            for axis in ("X", "Y", "Z", "total")
        )

    total = math.sqrt(
        acceleration.x**2 + acceleration.y**2 + acceleration.z**2
    )
    return (
        (f"{label_prefix} X", _format(acceleration.x, "m/s²", 3)),
        (f"{label_prefix} Y", _format(acceleration.y, "m/s²", 3)),
        (f"{label_prefix} Z", _format(acceleration.z, "m/s²", 3)),
        (f"{label_prefix} total", _format(total, "m/s²", 3)),
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
        screen.addnstr(
            row,
            column,
            text,
            max(0, width - column - 1),
            attributes,
        )
    except curses.error:
        pass


def _render(
    screen: curses.window,
    state: NavigationState | None,
    status: str,
    connected: bool,
    gps_enabled: bool,
    acceleration_mode: str,
) -> None:
    screen.erase()
    height, width = screen.getmaxyx()

    title_attr = curses.A_BOLD
    if curses.has_colors():
        title_attr |= curses.color_pair(1)
    _addstr(screen, 0, 2, "OpenRoadCode Navigation State", title_attr)
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

    fields = _fields(state, gps_enabled, acceleration_mode)
    two_columns = width >= 84
    rows_per_column = (
        (len(fields) + 1) // 2 if two_columns else len(fields)
    )
    column_width = width // 2 if two_columns else width

    for index, (label, value) in enumerate(fields):
        column_index = index // rows_per_column if two_columns else 0
        row_index = index % rows_per_column if two_columns else index
        row = 4 + row_index
        column = 2 + column_index * column_width
        _addstr(screen, row, column, f"{label:<21}", curses.A_DIM)
        _addstr(screen, row, column + 22, value, curses.A_BOLD)

    footer_row = min(height - 3, 5 + rows_per_column)
    _addstr(screen, footer_row, 0, "─" * max(0, width - 1))
    _addstr(screen, footer_row + 1, 2, status)

    controls = (
        "q: quit   h: reset heading   c: calibrate   "
        f"a: acceleration ({acceleration_mode})"
    )
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
        time.sleep(0.02)
    return -1


def _run(
    screen: curses.window,
    controller: NavigationController,
    refresh_seconds: float,
    gps_enabled: bool,
    acceleration_mode: str,
    calibration_samples: int,
    calibration_interval_s: float,
    calibrate_on_start: bool,
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

    state: NavigationState | None = None
    connected = False
    status = "Starting..."
    current_acceleration_mode = acceleration_mode

    def calibrate() -> str:
        _render(
            screen,
            state,
            "Calibrating; keep the vehicle completely still...",
            connected,
            gps_enabled,
            current_acceleration_mode,
        )
        try:
            result = controller.calibrate_stationary(
                sample_count=calibration_samples,
                sample_interval_s=calibration_interval_s,
            )
        except Exception as exc:
            return f"Calibration error: {exc}"
        return f"Calibrated from {result.sample_count} stationary samples"

    while True:
        key = screen.getch()
        if key in (ord("q"), ord("Q")):
            return
        if key in (ord("h"), ord("H")) and connected:
            controller.reset_heading()
            status = "Relative heading reset to 0°"
        if key in (ord("a"), ord("A")):
            current_acceleration_mode = _next_acceleration_mode(
                current_acceleration_mode
            )
            status = (
                f"Acceleration display: {current_acceleration_mode}"
            )
        if key in (ord("c"), ord("C")) and connected:
            status = calibrate()

        if not connected:
            try:
                status = "Connecting to navigation sensors..."
                _render(
                    screen,
                    state,
                    status,
                    connected,
                    gps_enabled,
                    current_acceleration_mode,
                )
                controller.start()
                connected = True
                status = (
                    calibrate()
                    if calibrate_on_start
                    else "Live navigation data"
                )
            except Exception as exc:
                status = f"Connection error: {exc}"

            _render(
                screen,
                state,
                status,
                connected,
                gps_enabled,
                current_acceleration_mode,
            )
            if not connected:
                while True:
                    key = _wait_for_key(screen, 0.1)
                    if key in (ord("q"), ord("Q")):
                        return
                    if key in (ord("r"), ord("R")):
                        break
                continue

        try:
            state = controller.read_state()
            if gps_enabled and state.gps is None:
                status = "Live IMU data; waiting for gpsd report"
            elif (
                gps_enabled
                and state.gps is not None
                and not state.gps.has_fix
            ):
                status = "Live IMU data; waiting for GPS fix"
            else:
                status = "Live navigation data"
            if controller.calibration is not None:
                status += "; stationary calibration active"
        except Exception as exc:
            connected = False
            status = f"Navigation error: {exc}"
            controller.stop()

        _render(
            screen,
            state,
            status,
            connected,
            gps_enabled,
            current_acceleration_mode,
        )
        key = _wait_for_key(screen, refresh_seconds)
        if key in (ord("q"), ord("Q")):
            return
        if key in (ord("h"), ord("H")) and connected:
            controller.reset_heading()
            status = "Relative heading reset to 0°"
        if key in (ord("a"), ord("A")):
            current_acceleration_mode = _next_acceleration_mode(
                current_acceleration_mode
            )
        if key in (ord("c"), ord("C")) and connected:
            status = calibrate()


def _next_acceleration_mode(current: str) -> str:
    index = ACCELERATION_MODES.index(current)
    return ACCELERATION_MODES[(index + 1) % len(ACCELERATION_MODES)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display live vehicle navigation state in a terminal."
    )
    parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        default=Mpu6050Imu.DEFAULT_ADDRESS,
        help="MPU-6050 I2C address. Default: 0x68",
    )
    parser.add_argument(
        "--refresh",
        type=float,
        default=0.1,
        help="Delay in seconds between navigation samples",
    )
    parser.add_argument(
        "--filter-time-constant",
        type=float,
        default=0.5,
        help="Complementary-filter time constant in seconds",
    )
    parser.add_argument(
        "--gps",
        action="store_true",
        help="Include GPS state from gpsd",
    )
    parser.add_argument("--gps-host", default="127.0.0.1")
    parser.add_argument("--gps-port", default="2947")
    parser.add_argument(
        "--acceleration-mode",
        choices=ACCELERATION_MODES,
        default="both",
        help="Acceleration fields to display. Default: both",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run stationary calibration immediately after connecting",
    )
    parser.add_argument(
        "--calibration-samples",
        type=int,
        default=100,
        help="Stationary samples used for calibration. Default: 100",
    )
    parser.add_argument(
        "--calibration-interval",
        type=float,
        default=0.01,
        help="Seconds between calibration samples. Default: 0.01",
    )
    args = parser.parse_args()

    if args.refresh <= 0:
        parser.error("--refresh must be greater than zero")
    if args.filter_time_constant < 0:
        parser.error("--filter-time-constant must be zero or greater")
    if args.calibration_samples <= 0:
        parser.error("--calibration-samples must be greater than zero")
    if args.calibration_interval < 0:
        parser.error("--calibration-interval must be zero or greater")
    return args


def _build_controller(args: argparse.Namespace) -> NavigationController:
    gps_source = None
    if args.gps:
        from hardware_io.gps import GpsReader

        gps_source = GpsdNavigationAdapter(
            GpsReader(host=args.gps_host, port=args.gps_port)
        )

    return NavigationController(
        sensor=Mpu6050NavigationAdapter(
            Mpu6050Imu(address=args.address)
        ),
        filter_time_constant_s=args.filter_time_constant,
        gps_source=gps_source,
    )


def main() -> int:
    args = parse_args()
    controller = _build_controller(args)

    try:
        curses.wrapper(
            _run,
            controller,
            args.refresh,
            args.gps,
            args.acceleration_mode,
            args.calibration_samples,
            args.calibration_interval,
            args.calibrate,
        )
    finally:
        controller.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
