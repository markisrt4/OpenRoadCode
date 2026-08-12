# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Standalone terminal composition for live vehicle navigation state."""

from __future__ import annotations

import argparse
import curses
import time

from controllers.navigation import (
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
)
from frontends.tui.automotive import ACCELERATION_MODES, NavigationDashboardView
from frontends.tui.automotive.navigation_dashboard_view import navigation_fields
from hardware_io.imu import Mpu6050Imu


_fields = navigation_fields


def _wait_for_key(screen, seconds: float) -> int:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        key = screen.getch()
        if key != -1:
            return key
        time.sleep(0.02)
    return -1


def _next_acceleration_mode(current: str) -> str:
    index = ACCELERATION_MODES.index(current)
    return ACCELERATION_MODES[(index + 1) % len(ACCELERATION_MODES)]


def _run(
    screen,
    controller: NavigationController,
    refresh_seconds: float,
    gps_enabled: bool,
    acceleration_mode: str,
    calibration_samples: int,
    calibration_interval_s: float,
    calibrate_on_start: bool,
) -> None:
    _configure_curses(screen)
    view = NavigationDashboardView()
    state = None
    connected = False
    status = "Starting..."
    current_mode = acceleration_mode

    def render() -> None:
        controls = (
            "q: quit   h: reset heading   c: calibrate   "
            f"a: acceleration ({current_mode})"
        )
        if not connected:
            controls += "   r: reconnect"
        view.render(
            screen, state, status, connected, gps_enabled, current_mode, controls
        )

    def calibrate() -> str:
        nonlocal status
        status = "Calibrating; keep the vehicle completely still..."
        render()
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
        if key in (ord("a"), ord("A")):
            current_mode = _next_acceleration_mode(current_mode)
        if key in (ord("h"), ord("H")) and connected:
            controller.reset_heading()
            status = "Relative heading reset to 0°"
        if key in (ord("c"), ord("C")) and connected:
            status = calibrate()

        if not connected:
            status = "Connecting to navigation sensors..."
            render()
            try:
                controller.start()
                connected = True
                status = calibrate() if calibrate_on_start else "Live navigation data"
            except Exception as exc:
                status = f"Connection error: {exc}"
            render()
            if not connected:
                key = _wait_for_key(screen, 0.1)
                if key in (ord("q"), ord("Q")):
                    return
                if key not in (ord("r"), ord("R")):
                    continue
                continue

        try:
            state = controller.read_state()
            status = "Live navigation data"
            if gps_enabled and state.gps is None:
                status = "Live IMU data; waiting for gpsd report"
            elif gps_enabled and not state.gps.has_fix:
                status = "Live IMU data; waiting for GPS fix"
            if controller.calibration is not None:
                status += "; stationary calibration active"
        except Exception as exc:
            connected = False
            status = f"Navigation error: {exc}"
            controller.stop()
        render()
        key = _wait_for_key(screen, refresh_seconds)
        if key != -1:
            curses.ungetch(key)


def _configure_curses(screen) -> None:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display live vehicle navigation state in a terminal."
    )
    parser.add_argument("--address", type=lambda value: int(value, 0), default=Mpu6050Imu.DEFAULT_ADDRESS)
    parser.add_argument("--refresh", type=float, default=0.1)
    parser.add_argument("--filter-time-constant", type=float, default=0.5)
    parser.add_argument("--gps", action="store_true")
    parser.add_argument("--gps-host", default="127.0.0.1")
    parser.add_argument("--gps-port", default="2947")
    parser.add_argument("--acceleration-mode", choices=ACCELERATION_MODES, default="both")
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--calibration-samples", type=int, default=100)
    parser.add_argument("--calibration-interval", type=float, default=0.01)
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
        gps_source = GpsdNavigationAdapter(GpsReader(host=args.gps_host, port=args.gps_port))
    return NavigationController(
        sensor=Mpu6050NavigationAdapter(Mpu6050Imu(address=args.address)),
        filter_time_constant_s=args.filter_time_constant,
        gps_source=gps_source,
    )


def main() -> int:
    args = parse_args()
    controller = _build_controller(args)
    try:
        curses.wrapper(
            _run, controller, args.refresh, args.gps, args.acceleration_mode,
            args.calibration_samples, args.calibration_interval, args.calibrate,
        )
    finally:
        controller.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
