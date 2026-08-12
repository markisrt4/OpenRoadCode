# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Standalone terminal composition for live OBD-II vehicle telemetry."""

from __future__ import annotations

import argparse
import curses
import time

from controllers.automotive.obd2 import Elm327ObdAdapter, Obd2Manager
from frontends.tui.automotive import VehicleDashboardView
from frontends.tui.automotive.vehicle_dashboard_view import vehicle_fields
from hardware_io.automotive.elm327 import Elm327Device
from protocols.obd2 import Obd2ConnectionError, Obd2Error


_fields = vehicle_fields


def _wait_for_key(screen, seconds: float) -> int:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        key = screen.getch()
        if key != -1:
            return key
        time.sleep(0.05)
    return -1


def _run(screen, manager: Obd2Manager, refresh_seconds: float) -> None:
    _configure_curses(screen)
    view = VehicleDashboardView()
    state = None
    connected = False
    status = "Starting..."
    while True:
        key = screen.getch()
        if key in (ord("q"), ord("Q")):
            return
        if not connected:
            status = "Connecting to ELM327..."
            view.render(screen, state, status, connected, "q: quit   r: reconnect")
            try:
                manager.connect()
                connected = True
                status = "Connected; polling vehicle state"
            except Obd2ConnectionError as exc:
                status = f"Connection error: {exc}"
            view.render(screen, state, status, connected)
            if not connected:
                key = _wait_for_key(screen, 0.1)
                if key in (ord("q"), ord("Q")):
                    return
                if key not in (ord("r"), ord("R")):
                    continue
                continue
        try:
            status = "Polling vehicle ECUs..."
            view.render(screen, state, status, connected)
            state = manager.read_state()
            status = "Live data; unsupported values are shown as --"
        except Obd2ConnectionError as exc:
            connected = False
            status = f"Connection lost: {exc}"
        except Obd2Error as exc:
            status = f"OBD-II warning: {exc}"
        view.render(screen, state, status, connected)
        key = _wait_for_key(screen, refresh_seconds)
        if key in (ord("q"), ord("Q")):
            return


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
        description="Display live OBD-II vehicle state in a terminal dashboard."
    )
    parser.add_argument("--port", default="/dev/rfcomm0")
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument("--refresh", type=float, default=0.5)
    parser.add_argument("--slow-refresh", type=float, default=5.0)
    args = parser.parse_args()
    if args.refresh < 0:
        parser.error("--refresh must be zero or greater")
    if args.slow_refresh <= 0:
        parser.error("--slow-refresh must be greater than zero")
    return args


def main() -> int:
    args = parse_args()
    manager = Obd2Manager(
        Elm327ObdAdapter(Elm327Device(port=args.port, baud=args.baud)),
        slow_poll_interval_seconds=args.slow_refresh,
    )
    try:
        curses.wrapper(_run, manager, args.refresh)
    finally:
        manager.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
