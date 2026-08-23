# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for navigation service pipeline composition."""

from config.service_runtime_config import (
    GpsInputConfig,
    GpsSimulationConfig,
    ImuInputConfig,
    NavigationServiceRuntimeConfig,
    SimulationProfileConfig,
)
from controllers.navigation import NavigationController
from controllers.navigation.simulated_navigation_sensor import SimulatedNavigationSensor
from controllers.navigation.simulated_position_source import SimulatedPositionSource
from services.navigation import navigation_service_cli
from services.navigation.navigation_service_cli import build_controller


def test_build_controller_supports_simulated_imu_and_gps() -> None:
    config = NavigationServiceRuntimeConfig(
        imu=ImuInputConfig(
            source="simulation",
            simulation=SimulationProfileConfig(profile="driving"),
        ),
        gps=GpsInputConfig(
            source="simulation",
            simulation=GpsSimulationConfig(profile="driving"),
        ),
    )

    controller = build_controller(config)

    assert isinstance(controller, NavigationController)
    assert isinstance(controller._sensor, SimulatedNavigationSensor)
    assert isinstance(controller._gps_source, SimulatedPositionSource)


def test_build_controller_supports_simulated_imu_with_device_gps(monkeypatch) -> None:
    class FakeGpsReader:
        def __init__(self, host: str, port: str) -> None:
            self.host = host
            self.port = port

    monkeypatch.setattr(
        navigation_service_cli,
        "_create_gps_reader",
        lambda host, port: FakeGpsReader(host, port),
    )
    config = NavigationServiceRuntimeConfig(
        imu=ImuInputConfig(source="simulation"),
        gps=GpsInputConfig(source="device", device="gpsd"),
    )

    controller = build_controller(config)

    assert isinstance(controller._sensor, SimulatedNavigationSensor)
    assert not isinstance(controller._gps_source, SimulatedPositionSource)


def test_build_controller_supports_device_imu_with_simulated_gps(monkeypatch) -> None:
    class FakeImu:
        def __init__(self, address: int) -> None:
            self.address = address

    monkeypatch.setattr(navigation_service_cli, "Mpu6050Imu", FakeImu)
    config = NavigationServiceRuntimeConfig(
        imu=ImuInputConfig(source="device", device="mpu6050"),
        gps=GpsInputConfig(source="simulation"),
    )

    controller = build_controller(config)

    assert not isinstance(controller._sensor, SimulatedNavigationSensor)
    assert isinstance(controller._gps_source, SimulatedPositionSource)
