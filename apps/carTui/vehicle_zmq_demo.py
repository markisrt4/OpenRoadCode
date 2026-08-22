# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Curses proof-of-concept consuming the public vehicle-state contract."""

from __future__ import annotations

import argparse
import curses
import math
import threading

from messaging.contracts.automotive import (
    VEHICLE_STATE_TOPIC,
    decode_vehicle_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber

RPM_PER_RAD_S = 60.0 / (2.0 * math.pi)
MPH_PER_MPS = 2.2369362920544
PSI_PER_PA = 0.00014503773773020923
KPA_PER_PA = 0.001
F_PER_K = 9.0 / 5.0
CTRL_X = 24


class VehicleUiState:
    """Thread-safe latest vehicle state consumed by the TUI renderer."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vehicle = None
        self._error = None

    def set_vehicle(self, message) -> None:
        with self._lock:
            self._vehicle = message
            self._error = None

    def set_error(self, topic, error) -> None:
        with self._lock:
            self._error = f"{topic}: {error}"

    def snapshot(self):
        with self._lock:
            return self._vehicle, self._error


def safe(window, row, col, text) -> None:
    height, width = window.getmaxyx()
    if 0 <= row < height and 0 <= col < width - 1:
        try:
            window.addstr(row, col, text[: width - col - 1])
        except curses.error:
            pass


def bar(value, maximum, width=24) -> str:
    if value is None:
        return "[" + " " * width + "]"
    count = max(0, min(width, round(value / maximum * width)))
    return "[" + "#" * count + "-" * (width - count) + "]"


def pct(value):
    return None if value is None else value * 100.0


def fahrenheit(kelvin):
    return None if kelvin is None else kelvin * F_PER_K - 459.67


def fmt(value, digits=1, suffix="") -> str:
    return "--" if value is None else f"{value:.{digits}f}{suffix}"


def draw(window, endpoint, ui_state) -> None:
    curses.curs_set(0)
    window.timeout(200)
    metric = False

    while True:
        message, error = ui_state.snapshot()
        window.erase()
        safe(window, 0, 0, "OpenRoadCode Vehicle Bus Demo")
        safe(window, 1, 0, f"Endpoint: {endpoint}")
        safe(window, 2, 0, f"Topic: {VEHICLE_STATE_TOPIC}")
        safe(window, 4, 0, f"q/Ctrl+X: quit   u: units   {'METRIC/SI' if metric else 'IMPERIAL'}")

        if error:
            safe(window, 6, 0, error)
        elif message is None:
            safe(window, 6, 0, "Waiting for vehicle-state messages...")
        else:
            d = message.data
            rpm = None if d.engine_speed_rad_s is None else d.engine_speed_rad_s * RPM_PER_RAD_S
            speed = d.vehicle_speed_m_s
            throttle = pct(d.throttle_position)
            pedal = pct(d.accelerator_pedal_position)
            load = pct(d.engine_load)
            fuel = pct(d.fuel_level)

            if metric:
                speed_text = fmt(speed, 1, " m/s")
                boost_text = fmt(None if d.boost_pressure_pa is None else d.boost_pressure_pa * KPA_PER_PA, 1, " kPa")
                coolant_text = fmt(None if d.coolant_temperature_k is None else d.coolant_temperature_k - 273.15, 1, " C")
                intake_text = fmt(None if d.intake_air_temperature_k is None else d.intake_air_temperature_k - 273.15, 1, " C")
            else:
                speed_text = fmt(None if speed is None else speed * MPH_PER_MPS, 1, " mph")
                boost_text = fmt(None if d.boost_pressure_pa is None else d.boost_pressure_pa * PSI_PER_PA, 1, " psi")
                coolant_text = fmt(fahrenheit(d.coolant_temperature_k), 1, " F")
                intake_text = fmt(fahrenheit(d.intake_air_temperature_k), 1, " F")

            rows = (
                ("Source", message.source),
                ("Engine", fmt(rpm, 0, " rpm")),
                ("Speed", speed_text),
                ("Throttle", fmt(throttle, 1, "%")),
                ("Pedal", fmt(pedal, 1, "%")),
                ("Engine load", fmt(load, 1, "%")),
                ("Boost", boost_text),
                ("Coolant", coolant_text),
                ("Intake air", intake_text),
                ("Fuel", fmt(fuel, 1, "%")),
                ("Voltage", fmt(d.control_voltage_v, 2, " V")),
            )
            for row, (label, value) in enumerate(rows, 6):
                safe(window, row, 0, f"{label:12}: {value}")

            safe(window, 18, 0, "THROTTLE " + bar(throttle, 100.0))
            safe(window, 19, 0, "LOAD     " + bar(load, 100.0))
            safe(window, 20, 0, "FUEL     " + bar(fuel, 100.0))

        window.refresh()
        key = window.getch()
        if key in (ord("q"), ord("Q"), CTRL_X):
            return
        if key in (ord("u"), ord("U")):
            metric = not metric


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5557")
    args = parser.parse_args()

    ui_state = VehicleUiState()
    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(args.endpoint),
        error_handler=ui_state.set_error,
    )
    dispatcher.register(
        VEHICLE_STATE_TOPIC,
        decode_vehicle_state,
        ui_state.set_vehicle,
    )
    dispatcher.start()
    try:
        curses.wrapper(draw, args.endpoint, ui_state)
    except KeyboardInterrupt:
        pass
    finally:
        dispatcher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
