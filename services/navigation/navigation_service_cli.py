# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the OpenRoadCode navigation telemetry and command service."""

from __future__ import annotations

import argparse

from controllers.navigation import (
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
    SimulatedNavigationController,
)
from hardware_io.imu import Mpu6050Imu
from messaging.zeromq import ZeroMqPublisher
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT
from services.navigation.navigation_runtime import NavigationRuntime
from services.navigation.zeromq_navigation_command_server import (
    DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish navigation telemetry and serve navigation commands."
    )
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--publisher-endpoint", default=LOCAL_PUBLISHER_ENDPOINT)
    parser.add_argument("--command-endpoint", default=DEFAULT_NAVIGATION_COMMAND_ENDPOINT)
    parser.add_argument("--rate-hz", type=float, default=10.0)
    parser.add_argument(
        "--address", type=lambda value: int(value, 0), default=Mpu6050Imu.DEFAULT_ADDRESS
    )
    parser.add_argument("--filter-time-constant", type=float, default=0.5)
    parser.add_argument("--gps", action="store_true")
    parser.add_argument("--gps-host", default="127.0.0.1")
    parser.add_argument("--gps-port", default="2947")
    args = parser.parse_args()
    if args.rate_hz <= 0.0:
        parser.error("--rate-hz must be greater than zero")
    if args.filter_time_constant < 0.0:
        parser.error("--filter-time-constant must be zero or greater")
    return args


def build_controller(args: argparse.Namespace):
    """Build the single controller owned by this service process."""
    if args.simulate:
        return SimulatedNavigationController()

    gps_source = None
    if args.gps:
        from hardware_io.gps import GpsReader

        gps_source = GpsdNavigationAdapter(
            GpsReader(host=args.gps_host, port=args.gps_port)
        )
    return NavigationController(
        sensor=Mpu6050NavigationAdapter(Mpu6050Imu(address=args.address)),
        filter_time_constant_s=args.filter_time_constant,
        gps_source=gps_source,
    )


def main() -> int:
    args = parse_args()
    publisher = ZeroMqPublisher(args.publisher_endpoint)
    runtime = NavigationRuntime(
        build_controller(args),
        publisher,
        source="simulated-navigation" if args.simulate else "navigation-service",
        rate_hz=args.rate_hz,
        command_endpoint=args.command_endpoint,
    )
    print("OpenRoadCode navigation service")
    print(f"  telemetry ingress: {args.publisher_endpoint}")
    print(f"  command endpoint:  {args.command_endpoint}")
    print(f"  publish rate:      {args.rate_hz:g} Hz")
    print(f"  source:            {'simulated-navigation' if args.simulate else 'navigation-service'}")
    print("Ctrl+C to stop")
    try:
        runtime.run()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.close()
        publisher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
