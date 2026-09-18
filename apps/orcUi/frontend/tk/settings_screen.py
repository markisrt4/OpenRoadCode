# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Settings-screen lifecycle for the integrated orcUi Tk frontend."""

from __future__ import annotations

from collections.abc import Callable

from controllers.automotive import AutomotiveTelemetryProfile, VehicleConfiguration
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle

from .screen_builders import build_settings_screen


class SettingsScreen(TkScreen):
    """Own the SETTINGS destination and its transient presentation."""

    SCREEN_ID = ScreenId("SETTINGS")

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        telemetry_profile_request: (
            Callable[[AutomotiveTelemetryProfile], None] | None
        ),
        vehicle_configuration: Callable[[], VehicleConfiguration],
        on_vehicle_configuration_changed: Callable[[VehicleConfiguration], None],
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(self.SCREEN_ID)
        self._host = host
        self._theme_bundle = theme_bundle
        self._telemetry_profile_request = telemetry_profile_request
        self._vehicle_configuration = vehicle_configuration
        self._on_vehicle_configuration_changed = on_vehicle_configuration_changed
        self._on_back = on_back

    def show(self) -> None:
        """Build SETTINGS content from the current shared configuration."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("SETTINGS")
        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.BACKGROUND)

        build_settings_screen(
            self._host.screen_parent,
            vehicle_configuration=self._vehicle_configuration(),
            on_vehicle_configuration_changed=self._on_vehicle_configuration_changed,
            on_back=self._on_back,
            theme=self._theme_bundle(),
        )
