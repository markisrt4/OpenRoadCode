# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Standalone terminal client for public navigation telemetry and commands."""

from __future__ import annotations

import argparse
import curses
import time

from apps.automotive_dashboard.navigation_bus_state import NavigationBusState
from frontends.tui.automotive import ACCELERATION_MODES, NavigationDashboardView
from frontends.tui.automotive.navigation_dashboard_view import navigation_fields
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    decode_attitude_state,
    decode_imu_state,
    decode_motion_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT
from services.navigation.endpoints import DEFAULT_NAVIGATION_COMMAND_ENDPOINT
from ui.navigation.navigation_request_handler_if import NavigationRequestHandlerIf


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
    state_cache: NavigationBusState,
    commands: NavigationRequestHandlerIf,
    refresh_seconds: float,
    gps_enabled: bool,
    acceleration_mode: str,
    calibrate_on_start: bool,
) -> None:
    _configure_curses(screen)
    view = NavigationDashboardView()
    current_mode = acceleration_mode
    command_status: str | None = None
    calibration_requested = False

    while True:
        snapshot = state_cache.snapshot()
        connected = snapshot.connected
        status = command_status or snapshot.status
        controls = (
            "q: quit   h: reset heading   c: calibrate   "
            f"a: acceleration ({current_mode})"
        )
        view.render(
            screen,
            snapshot,
            status,
            connected,
            gps_enabled,
            current_mode,
            controls,
        )

        if calibrate_on_start and connected and not calibration_requested:
            calibration_requested = True
            try:
                commands.request_stationary_calibration()
                command_status = "Stationary calibration complete"
            except Exception as exc:
                command_status = f"Calibration error: {exc}"

        key = _wait_for_key(screen, refresh_seconds)
        if key in (ord("q"), ord("Q")):
            return
        if key in (ord("a"), ord("A")):
            current_mode = _next_acceleration_mode(current_mode)
            command_status = None
        elif key in (ord("h"), ord("H")) and connected:
            try:
                commands.request_heading_reset()
                command_status = "Relative heading reset to 0°"
            except Exception as exc:
                command_status = f"Heading reset error: {exc}"
        elif key in (ord("c"), ord("C")) and connected:
            try:
                commands.request_stationary_calibration()
                command_status = "Stationary calibration complete"
            except Exception as exc:
                command_status = f"Calibration error: {exc}"
        elif key != -1:
            command_status = None


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
        description="Display public navigation bus telemetry in a terminal."
    )
    parser.add_argument("--endpoint", default=LOCAL_SUBSCRIBER_ENDPOINT)
    parser.add_argument("--command-endpoint", default=DEFAULT_NAVIGATION_COMMAND_ENDPOINT)
    parser.add_argument("--refresh", type=float, default=0.1)
    parser.add_argument("--gps", action="store_true")
    parser.add_argument("--acceleration-mode", choices=ACCELERATION_MODES, default="both")
    parser.add_argument("--calibrate", action="store_true")
    args = parser.parse_args()
    if args.refresh <= 0:
        parser.error("--refresh must be greater than zero")
    return args


def _build_dispatcher(endpoint: str, state: NavigationBusState) -> MessageDispatcher:
    from messaging.zeromq.subscriber import ZeroMqSubscriber

    dispatcher = MessageDispatcher(ZeroMqSubscriber(endpoint), error_handler=state.set_error)
    dispatcher.register(ATTITUDE_STATE_TOPIC, decode_attitude_state, state.set_attitude)
    dispatcher.register(IMU_STATE_TOPIC, decode_imu_state, state.set_imu)
    dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, state.set_position)
    dispatcher.register(MOTION_STATE_TOPIC, decode_motion_state, state.set_motion)
    return dispatcher


def main() -> int:
    from services.navigation.zeromq_navigation_request_handler import (
        ZeroMqNavigationRequestHandler,
    )

    args = parse_args()
    state = NavigationBusState()
    dispatcher = _build_dispatcher(args.endpoint, state)
    commands = ZeroMqNavigationRequestHandler(args.command_endpoint)
    dispatcher.start()
    try:
        curses.wrapper(
            _run,
            state,
            commands,
            args.refresh,
            args.gps,
            args.acceleration_mode,
            args.calibrate,
        )
    finally:
        commands.close()
        dispatcher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
