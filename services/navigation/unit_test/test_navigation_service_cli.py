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
from controllers.navigation.route_playback_position_source import RoutePlaybackPositionSource
from controllers.navigation.fallback_position_source import FallbackPositionSource
from controllers.navigation.browser_position_source import BrowserPositionSource
from controllers.navigation.route_simulation_if import RouteSimulationIf
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
    assert isinstance(controller._gps_source, RoutePlaybackPositionSource)
    assert isinstance(controller._gps_source, RouteSimulationIf)


def test_android_live_position_source_supports_local_route_playback() -> None:
    config = NavigationServiceRuntimeConfig(
        imu=ImuInputConfig(source="simulation"),
        gps=GpsInputConfig(source="device", device="android"),
    )
    source = navigation_service_cli._build_position_source(config)
    assert isinstance(source, RoutePlaybackPositionSource)
    assert isinstance(source, RouteSimulationIf)


def test_desktop_android_source_offers_loopback_browser_fallback(monkeypatch) -> None:
    monkeypatch.setattr(navigation_service_cli, "_host_location_fallback_available", lambda: True)
    monkeypatch.setenv("OPENROADCODE_BROWSER_POSITION_PORT", "9876")
    source = navigation_service_cli._build_position_source(
        NavigationServiceRuntimeConfig(gps=GpsInputConfig(device="android"))
    )
    assert isinstance(source._live_source, FallbackPositionSource)
    assert source._live_source._fallback.url == 'http://localhost:9876/'


def test_termux_keeps_bridge_source_without_browser_listener(monkeypatch) -> None:
    from controllers.navigation.android_position_source import AndroidPositionSource
    monkeypatch.setattr(navigation_service_cli, "_host_location_fallback_available", lambda: False)
    source = navigation_service_cli._build_position_source(
        NavigationServiceRuntimeConfig(gps=GpsInputConfig(device="android"))
    )
    assert isinstance(source._live_source, AndroidPositionSource)


def test_desktop_fallback_ignores_saved_rpi_build_target(monkeypatch) -> None:
    monkeypatch.setattr(navigation_service_cli.sys, "platform", "linux")
    monkeypatch.delenv("TERMUX_VERSION", raising=False)
    monkeypatch.delenv("PREFIX", raising=False)
    monkeypatch.setenv("OPENROAD_INSTALL_TARGET", "rpi5")
    monkeypatch.setattr(navigation_service_cli.Path, "read_text", lambda *args, **kwargs: "")
    source = navigation_service_cli._build_position_source(
        NavigationServiceRuntimeConfig(gps=GpsInputConfig(device="android"))
    )
    assert isinstance(source._live_source, FallbackPositionSource)


def test_actual_pi_hardware_does_not_offer_desktop_listener(monkeypatch) -> None:
    monkeypatch.setattr(navigation_service_cli.sys, "platform", "linux")
    monkeypatch.delenv("TERMUX_VERSION", raising=False)
    monkeypatch.delenv("PREFIX", raising=False)
    monkeypatch.setenv("OPENROAD_INSTALL_TARGET", "linux-dev")
    monkeypatch.setattr(navigation_service_cli.Path, "read_text",
                        lambda *args, **kwargs: "Raspberry Pi 5 Model B Rev 1.0\0")
    assert not navigation_service_cli._host_location_fallback_available()


def test_actual_termux_runtime_does_not_offer_desktop_listener(monkeypatch) -> None:
    monkeypatch.setattr(navigation_service_cli.sys, "platform", "linux")
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    monkeypatch.setenv("OPENROAD_INSTALL_TARGET", "linux-dev")
    assert not navigation_service_cli._host_location_fallback_available()


def test_browser_only_source_is_accepted_by_configuration_and_composition(tmp_path) -> None:
    from config.service_runtime_config import ServiceRuntimeConfigParser
    configuration = tmp_path / 'runtime.toml'
    configuration.write_text('[services.navigation.inputs.gps]\nsource = "browser"\n')
    config = ServiceRuntimeConfigParser(configuration).load().navigation
    assert config.gps.source == 'browser'
    assert isinstance(navigation_service_cli._build_position_source(config), BrowserPositionSource)


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
