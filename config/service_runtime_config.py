# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""System-level messaging and producer-service runtime configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT, LOCAL_SUBSCRIBER_ENDPOINT
from services.navigation.zeromq_navigation_command_server import DEFAULT_NAVIGATION_COMMAND_ENDPOINT


class ServiceRuntimeConfigError(ValueError):
    """Raised when system service runtime configuration is invalid."""


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
    port: str = "/dev/rfcomm0"
    baud: int = 38400
    timeout_s: float = 1.0
    slow_poll_interval_s: float = 5.0


@dataclass(frozen=True, slots=True)
class AutomotivePublishConfig:
    enabled: bool = True
    source: str = "automotive-service"


@dataclass(frozen=True, slots=True)
class AutomotiveServiceRuntimeConfig:
    enabled: bool = True
    rate_hz: float = 10.0
    input: AutomotiveInputConfig = AutomotiveInputConfig()
    publish: AutomotivePublishConfig = AutomotivePublishConfig()


@dataclass(frozen=True, slots=True)
class ServiceRuntimeConfig:
    messaging: MessagingRuntimeConfig = MessagingRuntimeConfig()
    navigation: NavigationServiceRuntimeConfig = NavigationServiceRuntimeConfig()
    automotive: AutomotiveServiceRuntimeConfig = AutomotiveServiceRuntimeConfig()


class ServiceRuntimeConfigParser:
    """Read service ownership and processing pipelines from runtime TOML."""

    def __init__(self, config_path: str | Path) -> None:
        self._path = Path(config_path).expanduser().resolve()

    def load(self) -> ServiceRuntimeConfig:
        try:
            with self._path.open("rb") as file:
                data = tomllib.load(file)
        except FileNotFoundError as exc:
            raise ServiceRuntimeConfigError(f"Runtime config file not found: {self._path}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ServiceRuntimeConfigError(f"Invalid TOML in {self._path}: {exc}") from exc

        messaging = self._parse_messaging(data.get("messaging", {}))
        services = self._table(data.get("services", {}), "services")
        navigation = self._parse_navigation(services.get("navigation", {}))
        automotive = self._parse_automotive(services.get("automotive", {}))
        return ServiceRuntimeConfig(messaging=messaging, navigation=navigation, automotive=automotive)

    def _parse_messaging(self, value) -> MessagingRuntimeConfig:
        data = self._table(value, "messaging")
        return MessagingRuntimeConfig(
            publisher_endpoint=self._string(data.get("publisher_endpoint", LOCAL_PUBLISHER_ENDPOINT), "messaging.publisher_endpoint"),
            subscriber_endpoint=self._string(data.get("subscriber_endpoint", LOCAL_SUBSCRIBER_ENDPOINT), "messaging.subscriber_endpoint"),
        )

    def _parse_navigation(self, value) -> NavigationServiceRuntimeConfig:
        data = self._table(value, "services.navigation")
        inputs = self._table(data.get("inputs", {}), "services.navigation.inputs")
        return NavigationServiceRuntimeConfig(
            enabled=self._bool(data.get("enabled", True), "services.navigation.enabled"),
            rate_hz=self._positive(data.get("rate_hz", 10.0), "services.navigation.rate_hz"),
            command_endpoint=self._string(data.get("command_endpoint", DEFAULT_NAVIGATION_COMMAND_ENDPOINT), "services.navigation.command_endpoint"),
            imu=self._parse_imu(inputs.get("imu", {})),
            gps=self._parse_gps(inputs.get("gps", {})),
            solution=self._parse_solution(data.get("solution", {})),
            publish=self._parse_publish(data.get("publish", {})),
            route_planning=self._parse_route_planning(data.get("route_planning", {})),
        )

    def _parse_automotive(self, value) -> AutomotiveServiceRuntimeConfig:
        data = self._table(value, "services.automotive")
        input_data = self._table(data.get("input", {}), "services.automotive.input")
        publish_data = self._table(data.get("publish", {}), "services.automotive.publish")
        source = self._source(input_data.get("source", "simulation"), "services.automotive.input.source")
        device = self._string(input_data.get("device", "elm327"), "services.automotive.input.device").lower()
        if source == "device" and device != "elm327":
            raise ServiceRuntimeConfigError("services.automotive.input.device must be elm327")
        baud = input_data.get("baud", 38400)
        if not isinstance(baud, int) or isinstance(baud, bool) or baud <= 0:
            raise ServiceRuntimeConfigError("services.automotive.input.baud must be a positive integer")
        return AutomotiveServiceRuntimeConfig(
            enabled=self._bool(data.get("enabled", True), "services.automotive.enabled"),
            rate_hz=self._positive(data.get("rate_hz", 10.0), "services.automotive.rate_hz"),
            input=AutomotiveInputConfig(
                source=source,
                device=device,
                port=self._string(input_data.get("port", "/dev/rfcomm0"), "services.automotive.input.port"),
                baud=baud,
                timeout_s=self._positive(input_data.get("timeout_s", 1.0), "services.automotive.input.timeout_s"),
                slow_poll_interval_s=self._positive(input_data.get("slow_poll_interval_s", 5.0), "services.automotive.input.slow_poll_interval_s"),
            ),
            publish=AutomotivePublishConfig(
                enabled=self._bool(publish_data.get("enabled", True), "services.automotive.publish.enabled"),
                source=self._string(publish_data.get("source", "automotive-service"), "services.automotive.publish.source"),
            ),
        )

    def _parse_imu(self, value) -> ImuInputConfig:
        data = self._table(value, "services.navigation.inputs.imu")
        source = self._source(data.get("source", "device"), "services.navigation.inputs.imu.source")
        device = self._string(data.get("device", "mpu6050"), "services.navigation.inputs.imu.device")
        if source == "device" and device != "mpu6050":
            raise ServiceRuntimeConfigError("services.navigation.inputs.imu.device must be mpu6050")
        address = data.get("address", 0x68)
        if not isinstance(address, int) or isinstance(address, bool) or not 0 <= address <= 0x7F:
            raise ServiceRuntimeConfigError("services.navigation.inputs.imu.address must be a valid 7-bit I2C address")
        simulation = self._table(data.get("simulation", {}), "services.navigation.inputs.imu.simulation")
        return ImuInputConfig(
            source=source,
            device=device,
            address=address,
            simulation=SimulationProfileConfig(profile=self._string(simulation.get("profile", "driving"), "services.navigation.inputs.imu.simulation.profile")),
        )

    def _parse_gps(self, value) -> GpsInputConfig:
        data = self._table(value, "services.navigation.inputs.gps")
        source = self._source(data.get("source", "device"), "services.navigation.inputs.gps.source")
        device = self._string(data.get("device", "gpsd"), "services.navigation.inputs.gps.device")
        if source == "device" and device != "gpsd":
            raise ServiceRuntimeConfigError("services.navigation.inputs.gps.device must be gpsd")
        simulation = self._table(data.get("simulation", {}), "services.navigation.inputs.gps.simulation")
        return GpsInputConfig(
            source=source,
            device=device,
            host=self._string(data.get("host", "127.0.0.1"), "services.navigation.inputs.gps.host"),
            port=self._string(str(data.get("port", "2947")), "services.navigation.inputs.gps.port"),
            simulation=GpsSimulationConfig(
                profile=self._string(simulation.get("profile", "driving"), "services.navigation.inputs.gps.simulation.profile"),
                latitude_deg=self._number(simulation.get("latitude_deg", 42.8028), "services.navigation.inputs.gps.simulation.latitude_deg"),
                longitude_deg=self._number(simulation.get("longitude_deg", -83.0127), "services.navigation.inputs.gps.simulation.longitude_deg"),
                speed_mps=self._number(simulation.get("speed_mps", 13.4), "services.navigation.inputs.gps.simulation.speed_mps"),
                course_deg=self._number(simulation.get("course_deg", 180.0), "services.navigation.inputs.gps.simulation.course_deg"),
            ),
        )

    def _parse_solution(self, value) -> NavigationSolutionConfig:
        data = self._table(value, "services.navigation.solution")
        algorithm = self._string(data.get("algorithm", "complementary_filter"), "services.navigation.solution.algorithm").lower()
        if algorithm != "complementary_filter":
            raise ServiceRuntimeConfigError("services.navigation.solution.algorithm must be complementary_filter")
        settings = self._table(data.get("complementary_filter", {}), "services.navigation.solution.complementary_filter")
        time_constant = self._number(settings.get("time_constant_s", 0.5), "services.navigation.solution.complementary_filter.time_constant_s")
        if time_constant < 0:
            raise ServiceRuntimeConfigError("services.navigation.solution.complementary_filter.time_constant_s must be non-negative")
        heading_reference = self._string(settings.get("heading_reference", "relative"), "services.navigation.solution.complementary_filter.heading_reference").lower()
        if heading_reference not in {"relative", "true", "magnetic"}:
            raise ServiceRuntimeConfigError("services.navigation.solution.complementary_filter.heading_reference must be relative, true, or magnetic")
        return NavigationSolutionConfig(
            algorithm=algorithm,
            complementary_filter=ComplementaryFilterConfig(time_constant_s=time_constant, heading_reference=heading_reference),
        )

    def _parse_publish(self, value) -> NavigationPublishConfig:
        data = self._table(value, "services.navigation.publish")
        return NavigationPublishConfig(
            enabled=self._bool(data.get("enabled", True), "services.navigation.publish.enabled"),
            source=self._string(data.get("source", "navigation-service"), "services.navigation.publish.source"),
        )

    def _parse_route_planning(self, value) -> RoutePlanningConfig:
        data = self._table(value, "services.navigation.route_planning")
        backend = self._string(data.get("backend", "valhalla"), "services.navigation.route_planning.backend").lower()
        if backend != "valhalla":
            raise ServiceRuntimeConfigError("services.navigation.route_planning.backend must be valhalla")
        return RoutePlanningConfig(
            enabled=self._bool(data.get("enabled", True), "services.navigation.route_planning.enabled"),
            backend=backend,
            base_url=self._string(data.get("base_url", "http://127.0.0.1:8002"), "services.navigation.route_planning.base_url"),
            timeout_seconds=self._positive(data.get("timeout_seconds", 10.0), "services.navigation.route_planning.timeout_seconds"),
        )

    @staticmethod
    def _table(value, name: str) -> dict:
        if not isinstance(value, dict):
            raise ServiceRuntimeConfigError(f"{name} must be a TOML table")
        return value

    @staticmethod
    def _string(value, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ServiceRuntimeConfigError(f"{name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _number(value, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ServiceRuntimeConfigError(f"{name} must be numeric")
        return float(value)

    def _positive(self, value, name: str) -> float:
        result = self._number(value, name)
        if result <= 0:
            raise ServiceRuntimeConfigError(f"{name} must be greater than zero")
        return result

    @staticmethod
    def _bool(value, name: str) -> bool:
        if not isinstance(value, bool):
            raise ServiceRuntimeConfigError(f"{name} must be boolean")
        return value

    def _source(self, value, name: str) -> str:
        source = self._string(value, name).lower()
        if source not in {"device", "simulation"}:
            raise ServiceRuntimeConfigError(f"{name} must be device or simulation")
        return source
