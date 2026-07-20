"""Router subsystem orchestration."""

from __future__ import annotations

from pathlib import Path

from .interface_probe import InterfaceProbe
from .network_manager_router import NetworkManagerRouter
from .router_config import RouterConfig
from .router_if import RouterIf
from .router_status import RouterStatus


class RouterManagerError(RuntimeError):
    """Raised when router orchestration fails."""


class RouterManager:
    """Coordinates router configuration, validation, and runtime control."""

    def __init__(
        self,
        config: RouterConfig,
        *,
        interface_probe: InterfaceProbe | None = None,
        router: RouterIf | None = None,
    ) -> None:
        self._config = config
        self._interface_probe = interface_probe or InterfaceProbe()
        self._router = router or self._create_router(config)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        interface_probe: InterfaceProbe | None = None,
        router: RouterIf | None = None,
    ) -> "RouterManager":
        """Create a manager from a TOML configuration file."""

        return cls(
            RouterConfig.load(path),
            interface_probe=interface_probe,
            router=router,
        )

    @property
    def config(self) -> RouterConfig:
        """Return the active router configuration."""

        return self._config

    @property
    def router(self) -> RouterIf:
        """Return the managed router implementation."""

        return self._router

    def validate(self) -> None:
        """Validate configured interfaces and required files."""

        wifi_config = self._config.lan_wifi
        wan_config = self._config.wan

        if wifi_config.enabled:
            if wifi_config.interface == wan_config.interface:
                raise RouterManagerError(
                    "WAN and Wi-Fi LAN interfaces cannot be the same"
                )

            interfaces = {
                interface.name: interface
                for interface in self._interface_probe.probe()
            }

            wifi_interface = interfaces.get(wifi_config.interface)

            if wifi_interface is None:
                raise RouterManagerError(
                    "Configured Wi-Fi LAN interface was not found: "
                    f"{wifi_config.interface}"
                )

            if not wifi_interface.supports_ap:
                raise RouterManagerError(
                    "Configured Wi-Fi interface does not support AP mode: "
                    f"{wifi_config.interface}"
                )

            if (
                wifi_config.driver is not None
                and wifi_interface.driver != wifi_config.driver
            ):
                raise RouterManagerError(
                    "Configured Wi-Fi driver does not match detected driver: "
                    f"expected {wifi_config.driver}, "
                    f"detected {wifi_interface.driver or '-'}"
                )

            if (
                wifi_config.usb_id is not None
                and wifi_interface.usb_id != wifi_config.usb_id
            ):
                raise RouterManagerError(
                    "Configured Wi-Fi USB ID does not match detected device: "
                    f"expected {wifi_config.usb_id}, "
                    f"detected {wifi_interface.usb_id or '-'}"
                )

            if not wifi_config.password_file.is_file():
                raise RouterManagerError(
                    "Wi-Fi password file does not exist: "
                    f"{wifi_config.password_file}"
                )

        if self._config.lan_ethernet.enabled:
            lan_interface = self._config.lan_ethernet.interface

            if not lan_interface:
                raise RouterManagerError(
                    "Wired LAN is enabled but no interface is configured"
                )

            if lan_interface == wan_config.interface:
                raise RouterManagerError(
                    "WAN and wired LAN interfaces cannot be the same"
                )

    def start(self) -> RouterStatus:
        """Validate and start the configured router."""

        self.validate()
        self._router.start_router()
        return self._router.get_status()

    def stop(self) -> RouterStatus:
        """Stop the configured router."""

        self._router.stop_router()
        return self._router.get_status()

    def restart(self) -> RouterStatus:
        """Validate and restart the configured router."""

        self.validate()
        self._router.restart_router()
        return self._router.get_status()

    def get_status(self) -> RouterStatus:
        """Return the current router status."""

        return self._router.get_status()

    @staticmethod
    def _create_router(config: RouterConfig) -> RouterIf:
        if config.wan.connection_type != "ethernet":
            raise RouterManagerError(
                "Unsupported WAN connection type: "
                f"{config.wan.connection_type}"
            )

        if not config.lan_wifi.enabled:
            raise RouterManagerError(
                "NetworkManagerRouter currently requires Wi-Fi LAN"
            )

        return NetworkManagerRouter(
            connection_name=config.router.name,
            wan_interface=config.wan.interface,
            lan_interface=config.lan_wifi.interface,
        )
