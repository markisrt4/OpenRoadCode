# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Command-line bootstrap for the OpenRoadCode Car TUI."""

from __future__ import annotations

import argparse
import curses
import os
from pathlib import Path

from apps.carTui.car_tui import CarTui
from apps.carTui.car_tui_dependencies import CarTuiDependencies
from apps.carTui.navigation_bus_state import NavigationBusState
from apps.carTui.radio_catalog import build_car_tui_radios
from apps.carTui.vehicle_bus_state import VehicleBusState
from config.runtime_config import RuntimeConfigParser
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    decode_attitude_state,
    decode_imu_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "runtime.toml"


def parse_args() -> argparse.Namespace:
    """Parse Car TUI application settings."""
    parser = argparse.ArgumentParser(
        description="Run the multi-screen OpenRoadCode terminal interface."
    )
    parser.add_argument("--gps", action="store_true")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Shared OpenRoadCode runtime TOML configuration",
    )
    parser.add_argument(
        "--demo",
        "--simulate",
        dest="simulate",
        action="store_true",
        help="Use software-simulated radio data; navigation and vehicle telemetry come from the shared bus",
    )
    return parser.parse_args()


def _create_telemetry_consumer() -> tuple[
    NavigationBusState,
    VehicleBusState,
    MessageDispatcher,
]:
    endpoint = os.environ.get(
        "OPENROADCODE_ZMQ_SUBSCRIBE_ENDPOINT",
        "tcp://127.0.0.1:5557",
    )
    navigation_state = NavigationBusState()
    vehicle_state = VehicleBusState()

    def handle_error(topic: str, error: Exception) -> None:
        if topic == VEHICLE_STATE_TOPIC:
            vehicle_state.set_error(topic, error)
        else:
            navigation_state.set_error(topic, error)

    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(endpoint),
        error_handler=handle_error,
    )
    dispatcher.register(
        VEHICLE_STATE_TOPIC,
        decode_vehicle_state,
        vehicle_state.set_vehicle,
    )
    dispatcher.register(
        ATTITUDE_STATE_TOPIC,
        decode_attitude_state,
        navigation_state.set_attitude,
    )
    dispatcher.register(
        IMU_STATE_TOPIC,
        decode_imu_state,
        navigation_state.set_imu,
    )
    dispatcher.start()
    return navigation_state, vehicle_state, dispatcher


def build_dependencies(args: argparse.Namespace) -> CarTuiDependencies:
    """Construct Car TUI shared telemetry consumers and radio controllers."""
    runtime_config = RuntimeConfigParser(
        getattr(args, "config", DEFAULT_CONFIG_PATH),
        project_root=PROJECT_ROOT,
    ).load()
    navigation_state, vehicle_state, telemetry_dispatcher = _create_telemetry_consumer()

    try:
        return CarTuiDependencies(
            navigation_state=navigation_state,
            vehicle_state=vehicle_state,
            telemetry_dispatcher=telemetry_dispatcher,
            radios=build_car_tui_radios(runtime_config, simulate=args.simulate),
        )
    except Exception:
        telemetry_dispatcher.close()
        raise


def main() -> int:
    """Build dependencies and run Car TUI inside curses."""
    args = parse_args()
    dependencies = build_dependencies(args)
    try:
        curses.wrapper(
            CarTui(dependencies, gps_enabled=args.gps or args.simulate).run
        )
    finally:
        dependencies.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
