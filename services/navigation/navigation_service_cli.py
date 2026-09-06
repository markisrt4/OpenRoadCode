# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the OpenRoadCode navigation telemetry and command service."""

from __future__ import annotations

import argparse
import os
from dataclasses import replace
from pathlib import Path

from config.service_runtime_config import (
    NavigationServiceRuntimeConfig,
    ServiceRuntimeConfigParser,
)
from controllers.geocoding.sqlite_geocoder import SqliteGeocoder
from controllers.navigation import (
    AndroidNavigationSensor,
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
)
from controllers.navigation.android_position_source import AndroidPositionSource
from controllers.navigation.simulated_ground_motion_source import SimulatedGroundMotionSource
from controllers.navigation.simulated_navigation_sensor import SimulatedNavigationSensor
from controllers.navigation.simulated_position_source import SimulatedPositionSource
from controllers.route_planning.valhalla_route_planning_controller import ValhallaRoutePlanningController
from hardware_io.android import AndroidImu, AndroidSensorBridgeClient
from hardware_io.imu import Mpu6050Imu
from messaging.zeromq import ZeroMqPublisher
from protocols.valhalla.valhalla_http_client import ValhallaHttpClient
from services.navigation.navigation_runtime import NavigationRuntime

DEFAULT_RUNTIME_CONFIG = Path(__file__).resolve().parents[2] / "config" / "runtime.toml"


def _default_search_database() -> Path:
    configured = os.environ.get("OPENROADCODE_SEARCH_DATABASE")
    if configured:
        return Path(configured).expanduser()
    data_home = os.environ.get("XDG_DATA_HOME")
    root = Path(data_home).expanduser() if data_home else Path.home() / ".local" / "share"
    return root / "openroadcode" / "maps" / "search" / "openroadcode-search.sqlite"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish navigation telemetry and serve navigation commands."
    )
    parser.add_argument("--config", default=str(DEFAULT_RUNTIME_CONFIG))
    parser.add_argument(
        "--search-database",
        default=str(_default_search_database()),
        help="Offline OpenRoadCode search database used for destination geocoding.",
    )
    return parser.parse_args()


def _apply_input_source_overrides(
    config: NavigationServiceRuntimeConfig,
) -> NavigationServiceRuntimeConfig:
    """Apply deployment-level input selection without mutating shared TOML."""
    imu_source = os.environ.get("OPENROADCODE_NAV_IMU_SOURCE")
    gps_source = os.environ.get("OPENROADCODE_NAV_GPS_SOURCE")

    if imu_source is not None:
        imu_source = imu_source.strip().lower()
        if imu_source not in {"device", "simulation"}:
            raise ValueError(
                "OPENROADCODE_NAV_IMU_SOURCE must be 'device' or 'simulation'"
            )
        config = replace(config, imu=replace(config.imu, source=imu_source))

    if gps_source is not None:
        gps_source = gps_source.strip().lower()
        if gps_source not in {"device", "simulation"}:
            raise ValueError(
                "OPENROADCODE_NAV_GPS_SOURCE must be 'device' or 'simulation'"
            )
        config = replace(config, gps=replace(config.gps, source=gps_source))

    return config


def _create_gps_reader(host: str, port: str):
    """Create the physical GPS reader without leaking it into composition tests."""
    from hardware_io.gps import GpsReader

    return GpsReader(host=host, port=port)


def _build_motion_sensor(config: NavigationServiceRuntimeConfig):
    if config.imu.source == "simulation":
        return SimulatedNavigationSensor(profile=config.imu.simulation.profile)

    if config.imu.device == "android":
        client = AndroidSensorBridgeClient(base_url=config.imu.bridge_url)
        return AndroidNavigationSensor(AndroidImu(client))

    if config.imu.device == "mpu6050":
        return Mpu6050NavigationAdapter(Mpu6050Imu(address=config.imu.address))

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

    if config.gps.device == "android":
        return AndroidPositionSource(AndroidSensorBridgeClient(base_url=config.gps.bridge_url))

    if config.gps.device == "gpsd":
        return GpsdNavigationAdapter(_create_gps_reader(config.gps.host, config.gps.port))

    raise ValueError(f"Unsupported GPS device: {config.gps.device}")


def _build_ground_motion_source(config: NavigationServiceRuntimeConfig):
    if config.gps.source != "simulation":
        return None

    simulation = config.gps.simulation
    return SimulatedGroundMotionSource(
        profile=simulation.profile,
        speed_mps=simulation.speed_mps,
        course_deg=simulation.course_deg,
    )


def build_controller(config: NavigationServiceRuntimeConfig, *, position_source=None):
    """Build the configured pre-publication navigation solution pipeline."""
    if config.solution.algorithm != "complementary_filter":
        raise ValueError(
            "Unsupported navigation solution algorithm: "
            f"{config.solution.algorithm}"
        )

    if position_source is None:
        position_source = _build_position_source(config)

    return NavigationController(
        sensor=_build_motion_sensor(config),
        filter_time_constant_s=config.solution.complementary_filter.time_constant_s,
        gps_source=position_source,
        ground_motion_source=_build_ground_motion_source(config),
    )


def build_route_planning_controller(config: NavigationServiceRuntimeConfig):
    """Build the configured optional route-planning capability."""
    route_config = config.route_planning

    if not route_config.enabled:
        return None

    if route_config.backend != "valhalla":
        raise ValueError(f"Unsupported route-planning backend: {route_config.backend}")

    client = ValhallaHttpClient(
        route_config.base_url,
        timeout_seconds=route_config.timeout_seconds,
    )
    return ValhallaRoutePlanningController(client)


def build_geocoder(database: str | Path):
    """Build offline geocoding when the deployed search database is present."""
    path = Path(database).expanduser()
    if not path.is_file():
        return None
    return SqliteGeocoder(path)


def main() -> int:
    args = parse_args()
    system = ServiceRuntimeConfigParser(args.config).load()
    config = _apply_input_source_overrides(system.navigation)

    if not config.enabled:
        print("Navigation service disabled by runtime configuration")
        return 0

    position_source = _build_position_source(config)
    controller = build_controller(config, position_source=position_source)
    route_planning_controller = build_route_planning_controller(config)
    geocoder = build_geocoder(args.search_database)
    route_simulator = (
        position_source if isinstance(position_source, SimulatedPositionSource) else None
    )

    publish_source = config.publish.source
    publisher = ZeroMqPublisher(system.messaging.publisher_endpoint)

    runtime = NavigationRuntime(
        controller,
        publisher,
        source=publish_source,
        rate_hz=config.rate_hz,
        command_endpoint=config.command_endpoint,
        route_planning_controller=route_planning_controller,
        geocoder=geocoder,
        route_simulator=route_simulator,
    )

    print("OpenRoadCode navigation service")
    print(f"  IMU source:        {config.imu.source}/{config.imu.device}")
    print(f"  GPS source:        {config.gps.source}/{config.gps.device}")
    print(f"  solution:          {config.solution.algorithm}")
    print(
        "  route planning:    "
        f"{config.route_planning.backend if config.route_planning.enabled else 'disabled'}"
    )
    print(f"  geocoding:         {'offline' if geocoder is not None else 'disabled'}")
    if geocoder is not None:
        print(f"  search database:   {Path(args.search_database).expanduser()}")
    print(f"  route simulation:  {'available' if route_simulator is not None else 'disabled'}")
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
