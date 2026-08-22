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
    while True:
        message, error = latest.snapshot()
        window.erase()
        window.addstr(0, 0, "OpenRoadCode ZMQ Position Demo")
        window.addstr(1, 0, f"Endpoint: {endpoint}")
        window.addstr(2, 0, f"Topic:    {POSITION_STATE_TOPIC}")
        window.addstr(4, 0, "q: quit")

        if error:
            window.addstr(6, 0, f"Subscriber error: {error}")
        elif message is None:
            window.addstr(6, 0, "Waiting for position messages...")
        else:
            data = message.data
            rows = (
                ("Source", message.source),
                ("Latitude", f"{_format(_degrees(data.latitude_rad), 6)} deg"),
                ("Longitude", f"{_format(_degrees(data.longitude_rad), 6)} deg"),
                ("Altitude", f"{_format(data.altitude_m, 1)} m"),
                ("Speed", f"{_format(data.speed_m_s, 2)} m/s"),
                ("Course", f"{_format(_degrees(data.course_rad), 1)} deg"),
                ("Accuracy", f"{_format(data.accuracy_m, 1)} m"),
                ("Fix mode", str(data.fix_mode) if data.fix_mode is not None else "--"),
                ("Cached", "YES" if data.is_cached else "NO - fresh fix"),
            )
            for index, (label, value) in enumerate(rows, start=6):
                window.addstr(index, 0, f"{label:10}: {value}")

        window.refresh()
        key = window.getch()
        if key in (ord("q"), ord("Q")):
            return


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
