# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose native Weather presentation and provider dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.weather import (
    GpsdWeatherLocationProvider,
    OpenMeteoWeatherProvider,
    WeatherController,
    WeatherLocation,
)
from frontends.tk.weather import WeatherScreen
from services.navigation.navigation_service_cli import DEFAULT_RUNTIME_CONFIG


@dataclass(slots=True)
class WeatherComposition:
    """Own Weather presentation resources created by the composition root."""

    screen: WeatherScreen
    controller: WeatherController


def configure_weather(app: OrcUiApp) -> WeatherComposition:
    """Compose GPS-backed Open-Meteo Weather with a configured location fallback."""
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
    screen = WeatherScreen(
        app,
        controller=controller,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )
    app.register_screen("WEATHER", screen, before="VISION")
    return WeatherComposition(screen=screen, controller=controller)
