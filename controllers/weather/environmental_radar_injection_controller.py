# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Select live or injected radar from Android environmental injector state."""

from __future__ import annotations

from hardware_io.android import AndroidSensorBridgeClient
from controllers.weather.providers import InjectedRadarProvider, RainViewerRadarProvider
from controllers.weather.weather_radar_controller import WeatherRadarController


class EnvironmentalRadarInjectionController:
    """Apply Android environmental injection state to the radar controller."""

    def __init__(
        self,
        radar: WeatherRadarController,
        bridge: AndroidSensorBridgeClient | None = None,
    ) -> None:
        self._radar = radar
        self._bridge = bridge or AndroidSensorBridgeClient()
        self._scenario = "OFF"

    @property
    def scenario(self) -> str:
        return self._scenario

    def refresh(self) -> str:
        """Read injector state and switch provider only when the scenario changes."""
        try:
            scenario = self._bridge.read_environmental_injection()
        except RuntimeError:
            scenario = "OFF"
        if scenario == self._scenario:
            return scenario

        self._scenario = scenario
        if scenario in {"CLEAR", "STORM", "SEVERE"}:
            self._radar.set_provider(InjectedRadarProvider(scenario))
        else:
            self._radar.set_provider(RainViewerRadarProvider())
        return scenario
