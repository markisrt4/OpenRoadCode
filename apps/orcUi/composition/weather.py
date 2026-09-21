# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose native Weather presentation and provider dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from common.units import UnitSystem, kelvin_to_celsius, kelvin_to_fahrenheit
from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.weather import (
    GpsdWeatherLocationProvider,
    OpenMeteoWeatherProvider,
    RadarPalette,
    RadarTileService,
    RainViewerRadarProvider,
    WeatherController,
    WeatherLocation,
    WeatherRadarController,
)
from controllers.weather.environmental_radar_injection_controller import EnvironmentalRadarInjectionController\nfrom frontends.tk.weather import WeatherScreen\nfrom services.navigation.navigation_service_cli import DEFAULT_RUNTIME_CONFIG


@dataclass(slots=True)
class WeatherComposition:
    """Own Weather presentation resources created by the composition root."""

    screen: WeatherScreen
    controller: WeatherController
    radar: WeatherRadarController
    radar_tiles: RadarTileService\n    radar_injection: EnvironmentalRadarInjectionController\n
    def close(self) -> None:
        self.radar_tiles.close()


def configure_weather(
    app: OrcUiApp,
    *,
    unit_system: Callable[[], UnitSystem] = lambda: UnitSystem.IMPERIAL,
    radar_palette: RadarPalette = RadarPalette.UNIVERSAL,
    on_weather_radio: Callable[[], None] | None = None,
    on_weather_status: Callable[[str], None] | None = None,
    map_renderer=None,
) -> WeatherComposition:
    """Compose GPS-backed Open-Meteo Weather with shared display preferences."""
    runtime_config = ServiceRuntimeConfigParser(DEFAULT_RUNTIME_CONFIG).load()
    simulated_fix = runtime_config.navigation.gps.simulation
    fallback_location = WeatherLocation(
        latitude=simulated_fix.latitude_deg,
        longitude=simulated_fix.longitude_deg,
        name="Configured fallback",
        source="runtime-config",
    )
    controller = WeatherController(
        OpenMeteoWeatherProvider(),
        location_provider=GpsdWeatherLocationProvider(),
        fallback_location=fallback_location,
    )
    def publish_weather_status(state) -> None:
        if on_weather_status is None:
            return
        value = state.current.temperature_k
        if value is None:
            temperature = "--°"
        elif unit_system() is UnitSystem.IMPERIAL:
            temperature = f"{kelvin_to_fahrenheit(value):.0f}°F"
        else:
            temperature = f"{kelvin_to_celsius(value):.0f}°C"
        condition = state.current.condition_label.lower()
        symbol = "⚡" if "thunder" in condition else "❄" if "snow" in condition else "☂" if "rain" in condition else "☀" if "clear" in condition else "☁"
        on_weather_status(f"{symbol}  {temperature}")

    if map_renderer is None:
        raise ValueError("map_renderer is required for weather radar")
    radar_tiles = RadarTileService()
    radar = WeatherRadarController(
        RainViewerRadarProvider(), map_renderer, palette=radar_palette, tile_service=radar_tiles
    )

    screen = WeatherScreen(
        app,
        controller=controller,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
        unit_system=unit_system,
        on_weather_radio=on_weather_radio,
        on_weather_state=publish_weather_status,
    )
    app.register_screen("WEATHER", screen, before="VISION")
    return WeatherComposition(
        screen=screen, controller=controller, radar=radar, radar_tiles=radar_tiles
    )
