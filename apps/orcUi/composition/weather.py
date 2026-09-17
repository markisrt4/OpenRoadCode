# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose native Weather presentation and provider dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from controllers.weather import GpsdWeatherLocationProvider, OpenMeteoWeatherProvider, WeatherController
from frontends.tk.weather import WeatherScreen


@dataclass(slots=True)
class WeatherComposition:
    """Own Weather presentation resources created by the composition root."""

    screen: WeatherScreen
    controller: WeatherController


def configure_weather(app: OrcUiApp) -> WeatherComposition:
    """Compose GPS-backed Open-Meteo Weather and register its native screen."""
    controller = WeatherController(
        OpenMeteoWeatherProvider(),
        location_provider=GpsdWeatherLocationProvider(),
    )
    screen = WeatherScreen(
        app,
        controller=controller,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )
    app.register_screen("WEATHER", screen, before="VISION")
    return WeatherComposition(screen=screen, controller=controller)
