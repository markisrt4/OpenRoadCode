# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the OpenRoadCode navigation telemetry and command service."""

from __future__ import annotations

import argparse
from pathlib import Path

from config.service_runtime_config import (
    NavigationServiceRuntimeConfig,
    ServiceRuntimeConfigParser,
)
from controllers.navigation import (
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
    SimulatedNavigationController,
)
from hardware_io.imu import Mpu6050Imu
from messaging.zeromq import ZeroMqPublisher
from services.navigation.navigation_runtime import NavigationRuntime

DEFAULT_RUNTIME_CONFIG = Path(__file__).resolve().parents[2] / "config" / "runtime.toml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish navigation telemetry and serve navigation commands."
    )
    parser.add_argument("--config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Override services.navigation.backend with the simulated controller",
    )
    return parser.parse_args()


def build_controller(config: NavigationServiceRuntimeConfig):
    """Build the single navigation solution generator owned by this service."""
    if config.backend == "simulated":
        return SimulatedNavigationController()

    gps_source = None
    if config.gps_enabled:
        from hardware_io.gps import GpsReader

        gps_source = GpsdNavigationAdapter(
            GpsReader(host=config.gps_host, port=config.gps_port)
        )
    return NavigationController(
        sensor=Mpu6050NavigationAdapter(Mpu6050Imu(address=config.imu_address)),
        filter_time_constant_s=config.filter_time_constant_s,
        gps_source=gps_source,
    )


def main() -> int:
    args = parse_args()
    system = ServiceRuntimeConfigParser(args.config).load()
    config = system.navigation
    if args.simulate:
        config = NavigationServiceRuntimeConfig(
            enabled=config.enabled,
            backend="simulated",
            source="simulated-navigation",
            rate_hz=config.rate_hz,
            command_endpoint=config.command_endpoint,
            imu_address=config.imu_address,
            filter_time_constant_s=config.filter_time_constant_s,
            gps_enabled=config.gps_enabled,
            gps_host=config.gps_host,
            gps_port=config.gps_port,
        )
    if not config.enabled:
        print("Navigation service disabled by runtime configuration")
        return 0

    publisher = ZeroMqPublisher(system.messaging.publisher_endpoint)
    runtime = NavigationRuntime(
        build_controller(config),
        publisher,
        source=config.source,
        rate_hz=config.rate_hz,
        command_endpoint=config.command_endpoint,
    )
    print("OpenRoadCode navigation service")
    print(f"  backend:           {config.backend}")
    print(f"  telemetry ingress: {system.messaging.publisher_endpoint}")
    print(f"  command endpoint:  {config.command_endpoint}")
    print(f"  publish rate:      {config.rate_hz:g} Hz")
    print(f"  source:            {config.source}")
    print(f"  GPS:               {'enabled' if config.gps_enabled else 'disabled'}")
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
