# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the OpenRoadCode navigation telemetry and command service."""

from __future__ import annotations

import argparse
from pathlib import Path

from config.service_runtime_config import NavigationServiceRuntimeConfig, ServiceRuntimeConfigParser
from controllers.navigation import GpsdNavigationAdapter, Mpu6050NavigationAdapter, NavigationController, SimulatedNavigationController
from hardware_io.imu import Mpu6050Imu
from messaging.zeromq import ZeroMqPublisher
from services.navigation.navigation_runtime import NavigationRuntime

DEFAULT_RUNTIME_CONFIG = Path(__file__).resolve().parents[2] / "config" / "runtime.toml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish navigation telemetry and serve navigation commands.")
    parser.add_argument("--config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Development override: use the existing full simulated navigation controller",
    )
    return parser.parse_args()


def build_controller(config: NavigationServiceRuntimeConfig):
    """Build the configured pre-publication navigation solution pipeline."""
    # Until the split simulated IMU/GPS adapters are implemented, a configuration
    # requesting both simulated inputs maps cleanly to the existing full simulator.
    if config.imu.source == "simulation" and config.gps.source == "simulation":
        return SimulatedNavigationController()
    if config.imu.source == "simulation" or config.gps.source == "simulation":
        raise ValueError(
            "Mixed device/simulation navigation inputs are configured correctly but "
            "their individual simulation adapters are not implemented yet"
        )

    if config.imu.device != "mpu6050":
        raise ValueError(f"Unsupported IMU device: {config.imu.device}")
    if config.gps.device != "gpsd":
        raise ValueError(f"Unsupported GPS device: {config.gps.device}")
    if config.solution.algorithm != "complementary_filter":
        raise ValueError(f"Unsupported navigation solution algorithm: {config.solution.algorithm}")

    from hardware_io.gps import GpsReader

    gps_source = GpsdNavigationAdapter(GpsReader(host=config.gps.host, port=config.gps.port))
    return NavigationController(
        sensor=Mpu6050NavigationAdapter(Mpu6050Imu(address=config.imu.address)),
        filter_time_constant_s=config.solution.complementary_filter.time_constant_s,
        gps_source=gps_source,
    )


def main() -> int:
    args = parse_args()
    system = ServiceRuntimeConfigParser(args.config).load()
    config = system.navigation
    if not config.enabled:
        print("Navigation service disabled by runtime configuration")
        return 0

    controller = SimulatedNavigationController() if args.simulate else build_controller(config)
    publish_source = "simulated-navigation" if args.simulate else config.publish.source
    publisher = ZeroMqPublisher(system.messaging.publisher_endpoint)
    runtime = NavigationRuntime(
        controller,
        publisher,
        source=publish_source,
        rate_hz=config.rate_hz,
        command_endpoint=config.command_endpoint,
    )
    print("OpenRoadCode navigation service")
    print(f"  IMU source:        {'full simulation' if args.simulate else config.imu.source}")
    print(f"  GPS source:        {'full simulation' if args.simulate else config.gps.source}")
    print(f"  solution:          {'simulated' if args.simulate else config.solution.algorithm}")
    print(f"  telemetry ingress: {system.messaging.publisher_endpoint}")
    print(f"  command endpoint:  {config.command_endpoint}")
    print(f"  publish rate:      {config.rate_hz:g} Hz")
    print(f"  publish source:    {publish_source}")
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
