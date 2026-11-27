# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Settings-screen lifecycle for the integrated orcUi Tk frontend."""

from __future__ import annotations

from collections.abc import Callable

from common.units import UnitSystem
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.automotive.automotive_telemetry_profile import AutomotiveTelemetryProfile
from ui.automotive.vehicle_configuration import VehicleConfiguration
from ui.navigation.host_location_ui_if import HostLocationRequestHandlerIf, HostLocationState
from ui.radio.radio_visualization_config import RadioVisualizationSettingsIf
from ui.radio.receiver_settings_if import ReceiverSettingsIf
from ui.radio.rf_hardware_config_if import RfHardwareConfigIf
from ui.screen_ui_if import ScreenId
from ui.system.audio_settings_if import AudioSettingsIf
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
        telemetry_profile_request: (Callable[[AutomotiveTelemetryProfile], None] | None),
        vehicle_configuration: Callable[[], VehicleConfiguration],
        on_vehicle_configuration_changed: Callable[[VehicleConfiguration], None],
        unit_system: Callable[[], UnitSystem],
        on_unit_system_changed: Callable[[UnitSystem], None],
        on_back: Callable[[], None],
        rf_hardware_config: RfHardwareConfigIf | None = None,
        rf_visualization_settings: RadioVisualizationSettingsIf | None = None,
        receiver_settings: ReceiverSettingsIf | None = None,
        audio_settings: AudioSettingsIf | None = None,
        performance_overlay_enabled: Callable[[], bool] | None = None,
        on_performance_overlay_changed: Callable[[bool], None] | None = None,
        configure_spotify: Callable[[], None] | None = None,
        close_spotify_configuration: Callable[[], None] = lambda: None,
    ) -> None:
        super().__init__(self.SCREEN_ID)
        self._host = host
        self._theme_bundle = theme_bundle
        self._telemetry_profile_request = telemetry_profile_request
        self._vehicle_configuration = vehicle_configuration
        self._on_vehicle_configuration_changed = on_vehicle_configuration_changed
        self._unit_system = unit_system
        self._on_unit_system_changed = on_unit_system_changed
        self._on_back = on_back
        self._rf_hardware_config = rf_hardware_config
        self._rf_visualization_settings = rf_visualization_settings
        self._receiver_settings = receiver_settings
        self._audio_settings = audio_settings
        self._performance_overlay_enabled = performance_overlay_enabled
        self._on_performance_overlay_changed = on_performance_overlay_changed
        self._host_location_handler: HostLocationRequestHandlerIf | None = None
        self._host_location_state = HostLocationState()
        self._panel = None
        self._configure_spotify = configure_spotify
        self._close_spotify_configuration = close_spotify_configuration

    def set_host_location_request_handler(self, handler: HostLocationRequestHandlerIf) -> None:
        self._host_location_handler = handler

    def set_host_location_state(self, state: HostLocationState) -> None:
        self._host_location_state = state
        if self._panel is not None:
            self._panel.set_host_location_state(state)

    def hide(self) -> None:
        self._close_spotify_configuration()
        self._panel = None
        if self._host_location_handler is not None:
            self._host_location_handler.hide()

    def set_theme_mode(self, _mode: object) -> None:
        """Rebuild active Settings content using the host's current theme."""
        self.show()

    def show(self) -> None:
        """Build SETTINGS content from the current shared configuration."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("SETTINGS")
        if self._telemetry_profile_request is not None:
            self._telemetry_profile_request(AutomotiveTelemetryProfile.BACKGROUND)

        self._panel = None
        if self._host_location_handler is not None:
            self._host_location_handler.show()
        self._panel = build_settings_screen(
            self._host.screen_parent,
            vehicle_configuration=self._vehicle_configuration(),
            on_vehicle_configuration_changed=self._on_vehicle_configuration_changed,
            unit_system=self._unit_system(),
            on_unit_system_changed=self._on_unit_system_changed,
            on_back=self._on_back,
            theme=self._theme_bundle(),
            host_location_handler=self._host_location_handler,
            host_location_state=self._host_location_state,
            rf_hardware_config=self._rf_hardware_config,
            rf_visualization_settings=self._rf_visualization_settings,
            receiver_settings=self._receiver_settings,
            audio_settings=self._audio_settings,
            performance_overlay_enabled=self._performance_overlay_enabled,
            on_performance_overlay_changed=self._on_performance_overlay_changed,
            configure_spotify=self._configure_spotify,
        )
