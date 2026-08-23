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

from messaging.zeromq.endpoints import (
    LOCAL_PUBLISHER_ENDPOINT,
    LOCAL_SUBSCRIBER_ENDPOINT,
)
from services.navigation.zeromq_navigation_command_server import (
    DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
)


class ServiceRuntimeConfigError(ValueError):
    """Raised when system service runtime configuration is invalid."""


@dataclass(frozen=True, slots=True)
class MessagingRuntimeConfig:
    """Configure the local process messaging fabric."""

    publisher_endpoint: str = LOCAL_PUBLISHER_ENDPOINT
    subscriber_endpoint: str = LOCAL_SUBSCRIBER_ENDPOINT


@dataclass(frozen=True, slots=True)
class NavigationServiceRuntimeConfig:
    """Configure ownership and solution generation in the navigation service."""

    enabled: bool = True
    backend: str = "mpu6050"
    source: str = "navigation-service"
    rate_hz: float = 10.0
    command_endpoint: str = DEFAULT_NAVIGATION_COMMAND_ENDPOINT
    imu_address: int = 0x68
    filter_time_constant_s: float = 0.5
    gps_enabled: bool = True
    gps_host: str = "127.0.0.1"
    gps_port: str = "2947"


@dataclass(frozen=True, slots=True)
class ServiceRuntimeConfig:
    """Contain configuration for shared producer services and messaging."""

    messaging: MessagingRuntimeConfig = MessagingRuntimeConfig()
    navigation: NavigationServiceRuntimeConfig = NavigationServiceRuntimeConfig()


class ServiceRuntimeConfigParser:
    """Read service ownership/configuration from the shared runtime TOML file."""

    def __init__(self, config_path: str | Path) -> None:
        self._path = Path(config_path).expanduser().resolve()

    def load(self) -> ServiceRuntimeConfig:
        try:
            with self._path.open("rb") as file:
                data = tomllib.load(file)
        except FileNotFoundError as exc:
            raise ServiceRuntimeConfigError(
                f"Runtime config file not found: {self._path}"
            ) from exc
        except tomllib.TOMLDecodeError as exc:
            raise ServiceRuntimeConfigError(
                f"Invalid TOML in {self._path}: {exc}"
            ) from exc

        messaging = self._parse_messaging(data.get("messaging", {}))
        services = self._table(data.get("services", {}), "services")
        navigation = self._parse_navigation(services.get("navigation", {}))
        return ServiceRuntimeConfig(messaging=messaging, navigation=navigation)

    def _parse_messaging(self, value) -> MessagingRuntimeConfig:
        data = self._table(value, "messaging")
        return MessagingRuntimeConfig(
            publisher_endpoint=self._string(
                data.get("publisher_endpoint", LOCAL_PUBLISHER_ENDPOINT),
                "messaging.publisher_endpoint",
            ),
            subscriber_endpoint=self._string(
                data.get("subscriber_endpoint", LOCAL_SUBSCRIBER_ENDPOINT),
                "messaging.subscriber_endpoint",
            ),
        )

    def _parse_navigation(self, value) -> NavigationServiceRuntimeConfig:
        data = self._table(value, "services.navigation")
        backend = self._string(data.get("backend", "mpu6050"), "services.navigation.backend").lower()
        if backend not in {"mpu6050", "simulated"}:
            raise ServiceRuntimeConfigError(
                "services.navigation.backend must be mpu6050 or simulated"
            )
        rate_hz = self._number(data.get("rate_hz", 10.0), "services.navigation.rate_hz")
        if rate_hz <= 0:
            raise ServiceRuntimeConfigError("services.navigation.rate_hz must be greater than zero")
        filter_time_constant_s = self._number(
            data.get("filter_time_constant_s", 0.5),
            "services.navigation.filter_time_constant_s",
        )
        if filter_time_constant_s < 0:
            raise ServiceRuntimeConfigError(
                "services.navigation.filter_time_constant_s must be non-negative"
            )
        imu_address = data.get("imu_address", 0x68)
        if not isinstance(imu_address, int) or isinstance(imu_address, bool) or not 0 <= imu_address <= 0x7F:
            raise ServiceRuntimeConfigError(
                "services.navigation.imu_address must be a valid 7-bit I2C address"
            )
        enabled = data.get("enabled", True)
        gps_enabled = data.get("gps_enabled", True)
        if not isinstance(enabled, bool):
            raise ServiceRuntimeConfigError("services.navigation.enabled must be boolean")
        if not isinstance(gps_enabled, bool):
            raise ServiceRuntimeConfigError("services.navigation.gps_enabled must be boolean")
        return NavigationServiceRuntimeConfig(
            enabled=enabled,
            backend=backend,
            source=self._string(data.get("source", "navigation-service"), "services.navigation.source"),
            rate_hz=rate_hz,
            command_endpoint=self._string(
                data.get("command_endpoint", DEFAULT_NAVIGATION_COMMAND_ENDPOINT),
                "services.navigation.command_endpoint",
            ),
            imu_address=imu_address,
            filter_time_constant_s=filter_time_constant_s,
            gps_enabled=gps_enabled,
            gps_host=self._string(data.get("gps_host", "127.0.0.1"), "services.navigation.gps_host"),
            gps_port=self._string(str(data.get("gps_port", "2947")), "services.navigation.gps_port"),
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
