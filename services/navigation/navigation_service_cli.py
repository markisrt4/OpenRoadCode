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
    AndroidNavigationSensor,
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
)
from controllers.navigation.simulated_navigation_sensor import (
    SimulatedNavigationSensor,
)
from controllers.navigation.simulated_position_source import SimulatedPositionSource
from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from hardware_io.android import AndroidImu, AndroidSensorBridgeClient
from hardware_io.imu import Mpu6050Imu
from messaging.zeromq import ZeroMqPublisher
from protocols.valhalla.valhalla_http_client import ValhallaHttpClient
from services.navigation.navigation_runtime import NavigationRuntime

DEFAULT_RUNTIME_CONFIG = (
    Path(__file__).resolve().parents[2] / "config" / "runtime.toml"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish navigation telemetry and serve navigation commands."
    )
    parser.add_argument("--config", default=str(DEFAULT_RUNTIME_CONFIG))
    return parser.parse_args()


def _create_gps_reader(host: str, port: str):
    """Create the physical GPS reader without leaking it into composition tests."""
    from hardware_io.gps import GpsReader

    return GpsReader(host=host, port=port)


def _build_motion_sensor(config: NavigationServiceRuntimeConfig):
    if config.imu.source == "simulation":
        return SimulatedNavigationSensor(
            profile=config.imu.simulation.profile
        )

    if config.imu.device == "android":
        client = AndroidSensorBridgeClient(
            base_url=config.imu.bridge_url
        )
        return AndroidNavigationSensor(AndroidImu(client))

    if config.imu.device == "mpu6050":
        return Mpu6050NavigationAdapter(
            Mpu6050Imu(address=config.imu.address)
        )

    raise ValueError(f"Unsupported IMU device: {config.imu.device}")


def _build_position_source(config: NavigationServiceRuntimeConfig):
    if config.gps.source == "simulation":
        simulation = config.gps.simulation
        return SimulatedPositionSource(
            profile=simulation.profile,
            latitude_deg=simulation.latitude_deg,
            longitude_deg=simulation.longitude_deg,
            speed_mps=simulation.speed_mps,
            course_deg=simulation.course_deg,
        )

    if config.gps.device != "gpsd":
        raise ValueError(f"Unsupported GPS device: {config.gps.device}")

    return GpsdNavigationAdapter(
        _create_gps_reader(config.gps.host, config.gps.port)
    )


def build_controller(config: NavigationServiceRuntimeConfig):
    """Build the configured pre-publication navigation solution pipeline."""
    if config.solution.algorithm != "complementary_filter":
        raise ValueError(
            "Unsupported navigation solution algorithm: "
            f"{config.solution.algorithm}"
        )

    return NavigationController(
        sensor=_build_motion_sensor(config),
        filter_time_constant_s=(
            config.solution.complementary_filter.time_constant_s
        ),
        gps_source=_build_position_source(config),
    )


def build_route_planning_controller(
    config: NavigationServiceRuntimeConfig,
):
    """Build the configured optional route-planning capability."""
    route_config = config.route_planning

    if not route_config.enabled:
        return None

    if route_config.backend != "valhalla":
        raise ValueError(
            f"Unsupported route-planning backend: {route_config.backend}"
        )

    client = ValhallaHttpClient(
        route_config.base_url,
        timeout_seconds=route_config.timeout_seconds,
    )
    return ValhallaRoutePlanningController(client)


def main() -> int:
    args = parse_args()
    system = ServiceRuntimeConfigParser(args.config).load()
    config = system.navigation

    if not config.enabled:
        print("Navigation service disabled by runtime configuration")
        return 0

    controller = build_controller(config)
    route_planning_controller = build_route_planning_controller(config)

    publish_source = config.publish.source
    publisher = ZeroMqPublisher(system.messaging.publisher_endpoint)

    runtime = NavigationRuntime(
        controller,
        publisher,
        source=publish_source,
        rate_hz=config.rate_hz,
        command_endpoint=config.command_endpoint,
        route_planning_controller=route_planning_controller,
    )

    print("OpenRoadCode navigation service")
    print(f"  IMU source:        {config.imu.source}/{config.imu.device}")
    print(f"  GPS source:        {config.gps.source}/{config.gps.device}")
    print(f"  solution:          {config.solution.algorithm}")
    print(
        "  route planning:    "
        f"{config.route_planning.backend if config.route_planning.enabled else 'disabled'}"
    )
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
