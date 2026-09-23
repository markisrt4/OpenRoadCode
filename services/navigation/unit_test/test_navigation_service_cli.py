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



def test_android_bridge_url_defaults_to_profile_configuration(monkeypatch) -> None:
    monkeypatch.delenv("OPENROADCODE_ANDROID_BRIDGE_URL", raising=False)

    assert (
        navigation_service_cli._android_bridge_url("http://127.0.0.1:8766")
        == "http://127.0.0.1:8766"
    )


def test_android_bridge_url_uses_service_manager_override(monkeypatch) -> None:
    monkeypatch.setenv(
        "OPENROADCODE_ANDROID_BRIDGE_URL", "http://192.168.1.50:8766"
    )

    assert (
        navigation_service_cli._android_bridge_url("http://127.0.0.1:8766")
        == "http://192.168.1.50:8766"
    )


def test_resolve_runtime_profile_defaults_to_local(monkeypatch) -> None:
    monkeypatch.delenv("OPENROADCODE_RUNTIME_PROFILE", raising=False)

    profile, path = navigation_service_cli.resolve_runtime_profile()

    assert profile == "local"
    assert path.name == "local.toml"


def test_resolve_runtime_profile_uses_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENROADCODE_RUNTIME_PROFILE", "remote")

    profile, path = navigation_service_cli.resolve_runtime_profile()

    assert profile == "remote"
    assert path.name == "remote.toml"


def test_navigation_profiles_parse_against_base_runtime() -> None:
    from config.service_runtime_config import ServiceRuntimeConfigParser

    expected = {
        "local": ("device", "android", "device", "android"),
        "remote": ("device", "mpu6050", "device", "gpsd"),
        "simulated": ("simulation", "mpu6050", "simulation", "gpsd"),
    }

    for profile, values in expected.items():
        _, overlay = navigation_service_cli.resolve_runtime_profile(profile)
        config = ServiceRuntimeConfigParser(
            navigation_service_cli.DEFAULT_RUNTIME_CONFIG,
            overlays=(overlay,),
        ).load().navigation

        assert (
            config.imu.source,
            config.imu.device,
            config.gps.source,
            config.gps.device,
        ) == values
