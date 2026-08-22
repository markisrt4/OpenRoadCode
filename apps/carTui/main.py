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
from apps.carTui.radio_catalog import build_car_tui_radios
from apps.carTui.vehicle_bus_state import VehicleBusState
from controllers.navigation import (
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
    SimulatedNavigationController,
)
from hardware_io.imu import Mpu6050Imu
from config.runtime_config import RuntimeConfigParser
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "runtime.toml"


def parse_args() -> argparse.Namespace:
    """Parse Car TUI hardware and controller settings."""
    parser = argparse.ArgumentParser(
        description="Run the multi-screen OpenRoadCode terminal interface."
    )
    parser.add_argument("--imu-address", type=lambda value: int(value, 0), default=0x68)
    parser.add_argument("--filter-time-constant", type=float, default=0.5)
    parser.add_argument("--gps", action="store_true")
    parser.add_argument("--gps-host", default="127.0.0.1")
    parser.add_argument("--gps-port", default="2947")
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
        help="Use software-simulated navigation and radio data; vehicle data comes from the shared bus",
    )
    args = parser.parse_args()
    if args.filter_time_constant < 0:
        parser.error("--filter-time-constant must be zero or greater")
    return args


def _create_vehicle_consumer() -> tuple[VehicleBusState, MessageDispatcher]:
    endpoint = os.environ.get(
        "OPENROADCODE_ZMQ_SUBSCRIBE_ENDPOINT",
        "tcp://127.0.0.1:5557",
    )
    vehicle_state = VehicleBusState()
    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(endpoint),
        error_handler=vehicle_state.set_error,
    )
    dispatcher.register(
        VEHICLE_STATE_TOPIC,
        decode_vehicle_state,
        vehicle_state.set_vehicle,
    )
    dispatcher.start()
    return vehicle_state, dispatcher


def build_dependencies(args: argparse.Namespace) -> CarTuiDependencies:
    """Construct Car TUI controllers and its shared vehicle bus consumer."""
    runtime_config = RuntimeConfigParser(
        getattr(args, "config", DEFAULT_CONFIG_PATH),
        project_root=PROJECT_ROOT,
    ).load()
    vehicle_state, vehicle_dispatcher = _create_vehicle_consumer()

    try:
        if args.simulate:
            navigation = SimulatedNavigationController()
        else:
            gps_source = None
            if args.gps:
                from hardware_io.gps import GpsReader

                gps_source = GpsdNavigationAdapter(
                    GpsReader(host=args.gps_host, port=args.gps_port)
                )
            navigation = NavigationController(
                sensor=Mpu6050NavigationAdapter(Mpu6050Imu(address=args.imu_address)),
                filter_time_constant_s=args.filter_time_constant,
                gps_source=gps_source,
            )

        return CarTuiDependencies(
            navigation_controller=navigation,
            vehicle_state=vehicle_state,
            vehicle_dispatcher=vehicle_dispatcher,
            radios=build_car_tui_radios(runtime_config, simulate=args.simulate),
        )
    except Exception:
        vehicle_dispatcher.close()
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
