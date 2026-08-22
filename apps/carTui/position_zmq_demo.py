# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Small curses proof-of-concept for the public ZMQ position contract."""

from __future__ import annotations

import argparse
import curses
import math
import threading

from messaging.contracts.navigation import POSITION_STATE_TOPIC, decode_position_state
from messaging.zeromq import ZeroMqSubscriber


MPH_PER_MPS = 2.2369362920544
FEET_PER_METER = 3.2808398950131

WORLD_MAP = (
    "             .-''''-.                       ",
    "        _.-''  _   _ ``-._                  ",
    "     .-'     .' '.   '.   '-.               ",
    "   .'      _/     \\    \\     '.             ",
    "  /      .'        '.   '.      \\            ",
    " ;      /   AMERICAS  \\   EUROPE ;           ",
    " |     ;              ;       /  |           ",
    " ;      \\            /  AFRICA   ;           ",
    "  \\      '.        .'      _.-'             ",
    "   '.       `-.__.-'    ASIA               ",
    "     '-._             _.-'                  ",
    "          `--.....--'                       ",
)


class LatestPosition:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._message = None
        self._error: str | None = None

    def set_message(self, message) -> None:
        with self._lock:
            self._message = message
            self._error = None

    def set_error(self, error: Exception) -> None:
        with self._lock:
            self._error = str(error)

    def snapshot(self):
        with self._lock:
            return self._message, self._error


def _degrees(value: float | None) -> float | None:
    return None if value is None else math.degrees(value)


def _format(value, digits: int = 2) -> str:
    return "--" if value is None else f"{value:.{digits}f}"


def _world_marker(latitude_rad: float | None, longitude_rad: float | None) -> tuple[int, int] | None:
    if latitude_rad is None or longitude_rad is None:
        return None
    latitude_deg = math.degrees(latitude_rad)
    longitude_deg = math.degrees(longitude_rad)
    width = max(len(line) for line in WORLD_MAP)
    height = len(WORLD_MAP)
    x = round((longitude_deg + 180.0) / 360.0 * (width - 1))
    y = round((90.0 - latitude_deg) / 180.0 * (height - 1))
    return max(0, min(height - 1, y)), max(0, min(width - 1, x))


def _draw_world(window, start_row: int, start_col: int, latitude_rad, longitude_rad) -> None:
    marker = _world_marker(latitude_rad, longitude_rad)
    for row_index, line in enumerate(WORLD_MAP):
        chars = list(line)
        if marker is not None and row_index == marker[0] and marker[1] < len(chars):
            chars[marker[1]] = "X"
        try:
            window.addstr(start_row + row_index, start_col, "".join(chars))
        except curses.error:
            pass


def _receiver(endpoint: str, latest: LatestPosition) -> None:
    subscriber = ZeroMqSubscriber(endpoint)
    subscriber.subscribe(POSITION_STATE_TOPIC)
    try:
        while True:
            _, payload = subscriber.receive()
            latest.set_message(decode_position_state(payload))
    except Exception as exc:
        latest.set_error(exc)
    finally:
        subscriber.close()


def _run(window, endpoint: str, latest: LatestPosition) -> None:
    curses.curs_set(0)
    window.timeout(200)
    metric = False

    while True:
        message, error = latest.snapshot()
        window.erase()
        window.addstr(0, 0, "OpenRoadCode ZMQ Position Demo")
        window.addstr(1, 0, f"Endpoint: {endpoint}")
        window.addstr(2, 0, f"Topic:    {POSITION_STATE_TOPIC}")
        window.addstr(4, 0, f"q: quit   u: units   Units: {'METRIC' if metric else 'IMPERIAL'}")

        if error:
            window.addstr(6, 0, f"Subscriber error: {error}")
        elif message is None:
            window.addstr(6, 0, "Waiting for position messages...")
        else:
            data = message.data
            latitude_deg = _degrees(data.latitude_rad)
            longitude_deg = _degrees(data.longitude_rad)
            course_deg = _degrees(data.course_rad)

            if metric:
                altitude = f"{_format(data.altitude_m, 1)} m"
                speed = f"{_format(data.speed_m_s, 2)} m/s"
                accuracy = f"{_format(data.accuracy_m, 1)} m"
            else:
                altitude = (
                    "-- ft"
                    if data.altitude_m is None
                    else f"{data.altitude_m * FEET_PER_METER:.1f} ft"
                )
                speed = (
                    "-- mph"
                    if data.speed_m_s is None
                    else f"{data.speed_m_s * MPH_PER_MPS:.1f} mph"
                )
                accuracy = (
                    "-- ft"
                    if data.accuracy_m is None
                    else f"{data.accuracy_m * FEET_PER_METER:.1f} ft"
                )

            rows = (
                ("Source", message.source),
                ("Latitude", f"{_format(latitude_deg, 6)} deg"),
                ("Longitude", f"{_format(longitude_deg, 6)} deg"),
                ("Altitude", altitude),
                ("Speed", speed),
                ("Course", f"{_format(course_deg, 1)} deg"),
                ("Accuracy", accuracy),
                ("Fix mode", str(data.fix_mode) if data.fix_mode is not None else "--"),
                ("Cached", "YES" if data.is_cached else "NO - fresh fix"),
            )
            for index, (label, value) in enumerate(rows, start=6):
                window.addstr(index, 0, f"{label:10}: {value}")

            world_col = 32
            window.addstr(6, world_col, "Your highly scientific world location:")
            _draw_world(window, 8, world_col, data.latitude_rad, data.longitude_rad)
            window.addstr(21, world_col, "X = you, approximately. Earth survived.")

        window.refresh()
        key = window.getch()
        if key in (ord("q"), ord("Q")):
            return
        if key in (ord("u"), ord("U")):
            metric = not metric


def main() -> int:
    parser = argparse.ArgumentParser(description="Display ZMQ position data in a TUI.")
    parser.add_argument(
        "--endpoint",
        default="tcp://127.0.0.1:5557",
        help="ZeroMQ publisher endpoint, e.g. tcp://192.168.8.20:5557",
    )
    args = parser.parse_args()

    latest = LatestPosition()
    thread = threading.Thread(
        target=_receiver,
        args=(args.endpoint, latest),
        name="position-zmq-subscriber",
        daemon=True,
    )
    thread.start()
    curses.wrapper(_run, args.endpoint, latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
