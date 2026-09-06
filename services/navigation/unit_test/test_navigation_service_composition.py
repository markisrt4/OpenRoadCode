# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Composition tests for configurable navigation service inputs."""

from config.service_runtime_config import (
    GpsInputConfig,
    GpsSimulationConfig,
    ImuInputConfig,
    NavigationServiceRuntimeConfig,
    SimulationProfileConfig,
)
from controllers.navigation.navigation_controller import NavigationController
from controllers.navigation.simulated_navigation_sensor import SimulatedNavigationSensor
from controllers.navigation.simulated_position_source import SimulatedPositionSource
from services.navigation import navigation_service_cli


class _FakeImuDevice:
    def __init__(self, address: int) -> None:
        self.address = address


class _FakeMotionAdapter:
    def __init__(self, device) -> None:
        self.device = device


class _FakeGpsReader:
    def __init__(self, host: str, port: str) -> None:
        self.host = host
        self.port = port


class _FakeGpsAdapter:
    def __init__(self, reader) -> None:
        self.reader = reader


def _config(imu_source: str, gps_source: str) -> NavigationServiceRuntimeConfig:
    return NavigationServiceRuntimeConfig(
        imu=ImuInputConfig(
            source=imu_source,
            device="mpu6050",
            address=0x68,
            simulation=SimulationProfileConfig(profile="driving"),
        ),
        gps=GpsInputConfig(
            source=gps_source,
            device="gpsd",
            host="127.0.0.1",
            port="2947",
            simulation=GpsSimulationConfig(profile="driving"),
        ),
    )


def _patch_devices(monkeypatch) -> None:
    monkeypatch.setattr(navigation_service_cli, "Mpu6050Imu", _FakeImuDevice)
    monkeypatch.setattr(navigation_service_cli, "Mpu6050NavigationAdapter", _FakeMotionAdapter)
    monkeypatch.setattr(navigation_service_cli, "GpsdNavigationAdapter", _FakeGpsAdapter)
    monkeypatch.setattr(
        navigation_service_cli,
        "_create_gps_reader",
        lambda host, port: _FakeGpsReader(host, port),
    )


def test_simulated_imu_and_simulated_gps_build_real_solution_controller():
    controller = navigation_service_cli.build_controller(
        _config("simulation", "simulation")
    )

    assert isinstance(controller, NavigationController)
    assert isinstance(controller._sensor, SimulatedNavigationSensor)
    assert isinstance(controller._gps_source, SimulatedPositionSource)


def test_simulated_imu_and_device_gps_can_be_composed(monkeypatch):
    _patch_devices(monkeypatch)
    controller = navigation_service_cli.build_controller(
        _config("simulation", "device")
    )

    assert isinstance(controller._sensor, SimulatedNavigationSensor)
    assert isinstance(controller._gps_source, _FakeGpsAdapter)


def test_device_imu_and_simulated_gps_can_be_composed(monkeypatch):
    _patch_devices(monkeypatch)
    controller = navigation_service_cli.build_controller(
        _config("device", "simulation")
    )

    assert isinstance(controller._sensor, _FakeMotionAdapter)
    assert isinstance(controller._gps_source, SimulatedPositionSource)


def test_device_imu_and_device_gps_can_be_composed(monkeypatch):
    _patch_devices(monkeypatch)
    controller = navigation_service_cli.build_controller(_config("device", "device"))

    assert isinstance(controller._sensor, _FakeMotionAdapter)
    assert isinstance(controller._gps_source, _FakeGpsAdapter)

def test_simulated_gps_uses_configured_speed_and_course():
    config = _config("simulation", "simulation")
    config = NavigationServiceRuntimeConfig(
        imu=config.imu,
        gps=GpsInputConfig(
            source="simulation",
            device="gpsd",
            host="127.0.0.1",
            port="2947",
            simulation=GpsSimulationConfig(
                profile="stationary",
                latitude_deg=42.8028,
                longitude_deg=-83.0127,
                speed_mps=0.0,
                course_deg=0.0,
            ),
        ),
    )

    controller = navigation_service_cli.build_controller(config)

    assert isinstance(controller._gps_source, SimulatedPositionSource)
    assert controller._gps_source._speed_mps == 0.0
    assert controller._gps_source._course_deg == 0.0
