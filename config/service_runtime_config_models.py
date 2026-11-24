# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed values produced by the runtime configuration parser."""

from __future__ import annotations

from dataclasses import dataclass

from controllers.automotive.vehicle_configuration import VehicleConfiguration
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT, LOCAL_SUBSCRIBER_ENDPOINT
from services.navigation.zeromq_navigation_command_server import DEFAULT_NAVIGATION_COMMAND_ENDPOINT


@dataclass(frozen=True, slots=True)
class MessagingRuntimeConfig:
    publisher_endpoint: str = LOCAL_PUBLISHER_ENDPOINT
    subscriber_endpoint: str = LOCAL_SUBSCRIBER_ENDPOINT


@dataclass(frozen=True, slots=True)
class SimulationProfileConfig:
    profile: str = "driving"


@dataclass(frozen=True, slots=True)
class ImuInputConfig:
    source: str = "device"
    device: str = "mpu6050"
    address: int = 0x68
    bridge_url: str = "http://127.0.0.1:8766"
    simulation: SimulationProfileConfig = SimulationProfileConfig()


@dataclass(frozen=True, slots=True)
class GpsSimulationConfig:
    profile: str = "driving"
    latitude_deg: float = 42.8028
    longitude_deg: float = -83.0127
    speed_mps: float = 13.4
    course_deg: float = 180.0


@dataclass(frozen=True, slots=True)
class GpsInputConfig:
    source: str = "device"
    device: str = "gpsd"
    host: str = "127.0.0.1"
    port: str = "2947"
    bridge_url: str = "http://127.0.0.1:8766"
    simulation: GpsSimulationConfig = GpsSimulationConfig()


@dataclass(frozen=True, slots=True)
class ComplementaryFilterConfig:
    time_constant_s: float = 0.5
    heading_reference: str = "relative"


@dataclass(frozen=True, slots=True)
class NavigationSolutionConfig:
    algorithm: str = "complementary_filter"
    complementary_filter: ComplementaryFilterConfig = ComplementaryFilterConfig()


@dataclass(frozen=True, slots=True)
class NavigationPublishConfig:
    enabled: bool = True
    source: str = "navigation-service"


@dataclass(frozen=True, slots=True)
class RoutePlanningConfig:
    enabled: bool = True
    backend: str = "valhalla"
    base_url: str = "http://127.0.0.1:8002"
    timeout_seconds: float = 10.0


@dataclass(frozen=True, slots=True)
class NavigationServiceRuntimeConfig:
    enabled: bool = True
    rate_hz: float = 10.0
    command_endpoint: str = DEFAULT_NAVIGATION_COMMAND_ENDPOINT
    imu: ImuInputConfig = ImuInputConfig()
    gps: GpsInputConfig = GpsInputConfig()
    solution: NavigationSolutionConfig = NavigationSolutionConfig()
    publish: NavigationPublishConfig = NavigationPublishConfig()
    route_planning: RoutePlanningConfig = RoutePlanningConfig()


@dataclass(frozen=True, slots=True)
class AutomotiveInputConfig:
    source: str = "simulation"
    device: str = "elm327"
    transport: str = "serial"
    port: str = "/dev/rfcomm0"
    baud: int = 38400
    host: str = "127.0.0.1"
    tcp_port: int = 35000
    timeout_s: float = 1.0
    request_rate_hz: float = 6.0


@dataclass(frozen=True, slots=True)
class AutomotiveFuelConfig:
    engine_displacement_l: float = 1.6
    volumetric_efficiency: float = 0.85


@dataclass(frozen=True, slots=True)
class AutomotivePublishConfig:
    enabled: bool = True
    source: str = "automotive-service"


@dataclass(frozen=True, slots=True)
class AutomotiveServiceRuntimeConfig:
    enabled: bool = True
    rate_hz: float = 10.0
    input: AutomotiveInputConfig = AutomotiveInputConfig()
    fuel: AutomotiveFuelConfig = AutomotiveFuelConfig()
    publish: AutomotivePublishConfig = AutomotivePublishConfig()


@dataclass(frozen=True, slots=True)
class EnvironmentalWeatherSimulationConfig:
    bridge_url: str = "http://127.0.0.1:8766"


@dataclass(frozen=True, slots=True)
class EnvironmentalServiceRuntimeConfig:
    weather_simulation: EnvironmentalWeatherSimulationConfig = (
        EnvironmentalWeatherSimulationConfig()
    )


@dataclass(frozen=True, slots=True)
class ServiceRuntimeConfig:
    messaging: MessagingRuntimeConfig = MessagingRuntimeConfig()
    navigation: NavigationServiceRuntimeConfig = NavigationServiceRuntimeConfig()
    automotive: AutomotiveServiceRuntimeConfig = AutomotiveServiceRuntimeConfig()
    environmental: EnvironmentalServiceRuntimeConfig = EnvironmentalServiceRuntimeConfig()
    vehicle: VehicleConfiguration = VehicleConfiguration()
