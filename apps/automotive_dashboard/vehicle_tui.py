# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Standalone terminal consumer of public vehicle telemetry."""

from __future__ import annotations

import argparse
import curses
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from common.units import UnitSystem
from frontends.tui.automotive import VehicleDashboardView
from frontends.tui.automotive.vehicle_dashboard_view import vehicle_fields
from messaging.contracts.automotive import (
    VEHICLE_STATE_TOPIC,
    VehicleStateMessage,
    decode_vehicle_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


_fields = vehicle_fields


@dataclass(frozen=True, slots=True)
class _VehicleDisplayState:
    timestamp: datetime
    engine_speed_rad_s: float | None
    vehicle_speed_m_s: float | None
    throttle_position: float | None
    accelerator_pedal_position: float | None
    engine_load: float | None
    intake_manifold_pressure_pa: float | None
    barometric_pressure_pa: float | None
    boost_pressure_pa: float | None
    mass_air_flow_kg_s: float | None
    coolant_temperature_k: float | None
    intake_air_temperature_k: float | None
    fuel_level: float | None
    control_voltage_v: float | None


class _VehicleBusCache:
    """Thread-safe latest-message cache for the standalone TUI."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._state: _VehicleDisplayState | None = None
        self._source: str | None = None
        self._count = 0
        self._error: str | None = None

    def set_message(self, message: VehicleStateMessage) -> None:
        data = message.data
        timestamp = datetime.fromtimestamp(
            message.timestamp.seconds
            + message.timestamp.nanoseconds / 1_000_000_000.0,
            tz=timezone.utc,
        )
        state = _VehicleDisplayState(
            timestamp=timestamp,
            engine_speed_rad_s=data.engine_speed_rad_s,
            vehicle_speed_m_s=data.vehicle_speed_m_s,
            throttle_position=data.throttle_position,
            accelerator_pedal_position=data.accelerator_pedal_position,
            engine_load=data.engine_load,
            intake_manifold_pressure_pa=data.intake_manifold_pressure_pa,
            barometric_pressure_pa=data.barometric_pressure_pa,
            boost_pressure_pa=data.boost_pressure_pa,
            mass_air_flow_kg_s=data.mass_air_flow_kg_s,
            coolant_temperature_k=data.coolant_temperature_k,
            intake_air_temperature_k=data.intake_air_temperature_k,
            fuel_level=data.fuel_level,
            control_voltage_v=data.control_voltage_v,
        )
        with self._lock:
            self._state = state
            self._source = message.source
            self._count += 1
            self._error = None

    def set_error(self, topic: str, error: Exception) -> None:
        with self._lock:
            self._error = f"Vehicle bus error [{topic}]: {type(error).__name__}: {error}"

    def snapshot(self) -> tuple[_VehicleDisplayState | None, bool, str]:
        with self._lock:
            if self._error is not None:
                return self._state, False, self._error
            if self._state is None:
                return None, False, "Waiting for vehicle telemetry"
            return (
                self._state,
                True,
                f"Live {self._source} · {self._count} messages",
            )


def _wait_for_key(screen, seconds: float) -> int:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        key = screen.getch()
        if key != -1:
            return key
        time.sleep(0.05)
    return -1


def _run(
    screen,
    cache: _VehicleBusCache,
    refresh_seconds: float,
    unit_system: UnitSystem,
) -> None:
    _configure_curses(screen)
    view = VehicleDashboardView(unit_system=unit_system)
    while True:
        state, connected, status = cache.snapshot()
        view.render(screen, state, status, connected, "q: quit")
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
        description="Display vehicle-state bus telemetry in a terminal dashboard."
    )
    parser.add_argument(
        "--endpoint",
        default=LOCAL_SUBSCRIBER_ENDPOINT,
        help="ZeroMQ broker subscriber endpoint",
    )
    parser.add_argument("--refresh", type=float, default=0.1)
    parser.add_argument(
        "--units",
        choices=tuple(system.value for system in UnitSystem),
        default=UnitSystem.IMPERIAL.value,
    )
    args = parser.parse_args()
    if args.refresh <= 0:
        parser.error("--refresh must be greater than zero")
    return args


def main() -> int:
    args = parse_args()
    cache = _VehicleBusCache()
    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(args.endpoint),
        error_handler=cache.set_error,
    )
    dispatcher.register(
        VEHICLE_STATE_TOPIC,
        decode_vehicle_state,
        cache.set_message,
    )
    dispatcher.start()
    try:
        curses.wrapper(
            _run,
            cache,
            args.refresh,
            UnitSystem(args.units),
        )
    finally:
        dispatcher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
