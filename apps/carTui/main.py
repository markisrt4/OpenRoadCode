"""Command-line bootstrap for the OpenRoadCode Car TUI."""

from __future__ import annotations

import argparse
import curses
from pathlib import Path

from apps.carTui.car_tui import CarTui
from apps.carTui.car_tui_dependencies import CarTuiDependencies
from apps.carTui.radio_catalog import build_car_tui_radios
from controllers.automotive import SimulatedVehicleStateSource
from controllers.automotive.obd2 import Elm327ObdAdapter, Obd2Manager
from controllers.navigation import (
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
    SimulatedNavigationController,
)
from hardware_io.automotive.elm327 import Elm327Device
from hardware_io.imu import Mpu6050Imu
from config.runtime_config import RuntimeConfigParser


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
    parser.add_argument("--obd-port", default="/dev/rfcomm0")
    parser.add_argument("--obd-baud", type=int, default=38400)
    parser.add_argument("--slow-refresh", type=float, default=5.0)
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
        help="Use software-simulated navigation, vehicle, and radio data",
    )
    args = parser.parse_args()
    if args.filter_time_constant < 0:
        parser.error("--filter-time-constant must be zero or greater")
    if args.slow_refresh <= 0:
        parser.error("--slow-refresh must be greater than zero")
    return args


def build_dependencies(args: argparse.Namespace) -> CarTuiDependencies:
    """Construct the statically configured Car TUI controller stacks."""
    runtime_config = RuntimeConfigParser(
        getattr(args, "config", DEFAULT_CONFIG_PATH),
        project_root=PROJECT_ROOT,
    ).load()
    if args.simulate:
        return CarTuiDependencies(
            SimulatedNavigationController(),
            SimulatedVehicleStateSource(),
            build_car_tui_radios(runtime_config, simulate=True),
        )

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
    vehicle = Obd2Manager(
        Elm327ObdAdapter(Elm327Device(port=args.obd_port, baud=args.obd_baud)),
        slow_poll_interval_seconds=args.slow_refresh,
    )
    return CarTuiDependencies(
        navigation,
        vehicle,
        build_car_tui_radios(runtime_config, simulate=False),
    )


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
