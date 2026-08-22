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
FPM_PER_MPS = 196.8503937007874
CTRL_X = 24
GRID_WIDTH = 31
GRID_HEIGHT = 11


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


def _degrees(value):
    return None if value is None else math.degrees(value)


def _format(value, digits=2):
    return "--" if value is None else f"{value:.{digits}f}"


def _compass_point(degrees):
    if degrees is None:
        return "--"
    names = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return names[round(degrees / 45.0) % 8]


def _bar(value, maximum, width=20):
    if value is None:
        return "[" + " " * width + "]"
    filled = max(0, min(width, round(abs(value) / maximum * width)))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _init_colors():
    if not curses.has_colors():
        return curses.A_BOLD
    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass
    curses.init_pair(1, curses.COLOR_BLUE, -1)
    return curses.color_pair(1) | curses.A_BOLD


def _safe_addstr(window, row, col, text, attr=0):
    max_y, max_x = window.getmaxyx()
    if row < 0 or row >= max_y or col < 0 or col >= max_x:
        return
    room = max_x - col - 1
    if room <= 0:
        return
    try:
        window.addstr(row, col, text[:room], attr)
    except curses.error:
        pass


def _draw_coordinate_grid(window, start_row, start_col, latitude_rad, longitude_rad, marker_attr):
    width, height = GRID_WIDTH, GRID_HEIGHT
    max_y, max_x = window.getmaxyx()
    if start_row + height + 2 >= max_y or start_col + width + 4 >= max_x:
        _safe_addstr(window, start_row, start_col, "[resize terminal to show position grid]")
        return
    top, left = start_row + 1, start_col + 2
    bottom, right = top + height - 1, left + width - 1
    for x in range(left, right + 1):
        window.addch(top, x, "+" if (x - left) % 7 == 0 else "-")
        window.addch(bottom, x, "+" if (x - left) % 7 == 0 else "-")
    for y in range(top + 1, bottom):
        window.addch(y, left, "|")
        window.addch(y, right, "|")
    equator_row = top + (height - 1) // 2
    prime_col = left + (width - 1) // 2
    for x in range(left + 1, right):
        window.addch(equator_row, x, "-")
    for y in range(top + 1, bottom):
        window.addch(y, prime_col, "|")
    window.addch(equator_row, prime_col, "+")
    _safe_addstr(window, start_row, left, "W             0°             E")
    _safe_addstr(window, top + 1, start_col, "N")
    _safe_addstr(window, bottom - 1, start_col, "S")
    if latitude_rad is None or longitude_rad is None:
        return
    latitude_deg, longitude_deg = math.degrees(latitude_rad), math.degrees(longitude_rad)
    marker_col = left + max(0, min(width - 1, round((longitude_deg + 180) / 360 * (width - 1))))
    marker_row = top + max(0, min(height - 1, round((90 - latitude_deg) / 180 * (height - 1))))
    for x in range(left + 1, right):
        window.addch(marker_row, x, "-")
    for y in range(top + 1, bottom):
        window.addch(y, marker_col, "|")
    try:
        window.addstr(marker_row, marker_col, "●", marker_attr)
    except (curses.error, UnicodeEncodeError):
        window.addch(marker_row, marker_col, "O", marker_attr)
    _safe_addstr(window, bottom + 1, left, f"{abs(latitude_deg):.4f}°{'N' if latitude_deg >= 0 else 'S'}  {abs(longitude_deg):.4f}°{'E' if longitude_deg >= 0 else 'W'}")


def _draw_motion(window, row, col, data, metric):
    course = _degrees(data.course_rad)
    direction = _compass_point(course)
    _safe_addstr(window, row, col, "MOTION")
    _safe_addstr(window, row + 1, col, f"Heading  {direction:>2}  {_format(course, 0):>3}°")

    if metric:
        speed_value = data.speed_m_s
        speed_text = "-- m/s" if speed_value is None else f"{speed_value:5.1f} m/s"
        climb_value = data.vertical_speed_m_s
        climb_text = "-- m/s" if climb_value is None else f"{climb_value:+5.2f} m/s"
        speed_max = 45.0
        climb_max = 8.0
    else:
        speed_value = None if data.speed_m_s is None else data.speed_m_s * MPH_PER_MPS
        speed_text = "-- mph" if speed_value is None else f"{speed_value:5.1f} mph"
        climb_value = None if data.vertical_speed_m_s is None else data.vertical_speed_m_s * FPM_PER_MPS
        climb_text = "-- ft/min" if climb_value is None else f"{climb_value:+6.0f} ft/min"
        speed_max = 100.0
        climb_max = 1500.0

    _safe_addstr(window, row + 3, col, f"Speed    {speed_text}")
    _safe_addstr(window, row + 4, col, _bar(speed_value, speed_max))

    if climb_value is None:
        arrow, label = "-", "VERTICAL"
    elif climb_value > 0.01:
        arrow, label = "^", "CLIMB"
    elif climb_value < -0.01:
        arrow, label = "v", "DESCENT"
    else:
        arrow, label = "-", "LEVEL"
    _safe_addstr(window, row + 6, col, f"{label:8} {arrow} {climb_text}")
    _safe_addstr(window, row + 7, col, _bar(climb_value, climb_max))


def _receiver(endpoint, latest):
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


def _run(window, endpoint, latest):
    curses.curs_set(0)
    marker_attr = _init_colors()
    window.timeout(200)
    metric = False
    while True:
        message, error = latest.snapshot()
        window.erase()
        _safe_addstr(window, 0, 0, "OpenRoadCode ZMQ Position Demo")
        _safe_addstr(window, 1, 0, f"Endpoint: {endpoint}")
        _safe_addstr(window, 2, 0, f"Topic:    {POSITION_STATE_TOPIC}")
        _safe_addstr(window, 4, 0, f"q/Ctrl+X: quit   u: units   Units: {'METRIC' if metric else 'IMPERIAL'}")
        if error:
            _safe_addstr(window, 6, 0, f"Subscriber error: {error}")
        elif message is None:
            _safe_addstr(window, 6, 0, "Waiting for position messages...")
        else:
            data = message.data
            latitude_deg, longitude_deg = _degrees(data.latitude_rad), _degrees(data.longitude_rad)
            if metric:
                altitude = f"{_format(data.altitude_m, 1)} m"
                accuracy = f"{_format(data.accuracy_m, 1)} m"
            else:
                altitude = "-- ft" if data.altitude_m is None else f"{data.altitude_m * FEET_PER_METER:.1f} ft"
                accuracy = "-- ft" if data.accuracy_m is None else f"{data.accuracy_m * FEET_PER_METER:.1f} ft"
            rows = (
                ("Source", message.source),
                ("Latitude", f"{_format(latitude_deg, 6)} deg"),
                ("Longitude", f"{_format(longitude_deg, 6)} deg"),
                ("Altitude", altitude),
                ("Accuracy", accuracy),
                ("Fix mode", str(data.fix_mode) if data.fix_mode is not None else "--"),
                ("Cached", "YES" if data.is_cached else "NO - fresh fix"),
            )
            for index, (label, value) in enumerate(rows, start=6):
                _safe_addstr(window, index, 0, f"{label:10}: {value}")

            _, max_x = window.getmaxyx()
            if max_x >= 100:
                _draw_motion(window, 6, 30, data, metric)
                grid_row, grid_col = 6, 62
            elif max_x >= 72:
                _draw_motion(window, 6, 34, data, metric)
                grid_row, grid_col = 16, 0
            else:
                _draw_motion(window, 14, 0, data, metric)
                grid_row, grid_col = 24, 0
            _safe_addstr(window, grid_row, grid_col, "Global latitude / longitude")
            _draw_coordinate_grid(window, grid_row + 1, grid_col, data.latitude_rad, data.longitude_rad, marker_attr)

        window.refresh()
        key = window.getch()
        if key in (ord("q"), ord("Q"), CTRL_X):
            return
        if key in (ord("u"), ord("U")):
            metric = not metric


def main():
    parser = argparse.ArgumentParser(description="Display ZMQ position data in a TUI.")
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5557")
    args = parser.parse_args()
    latest = LatestPosition()
    threading.Thread(target=_receiver, args=(args.endpoint, latest), name="position-zmq-subscriber", daemon=True).start()
    try:
        curses.wrapper(_run, args.endpoint, latest)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
