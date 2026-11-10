# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

from unittest.mock import Mock, patch

from apps.orcUi.composition.weather import configure_weather


@patch("apps.orcUi.composition.weather.WeatherScreenController")
@patch("apps.orcUi.composition.weather.WeatherScreen")
@patch("apps.orcUi.composition.weather.EnvironmentalRadarInjectionController")
@patch("apps.orcUi.composition.weather.AndroidSensorBridgeClient")
@patch("apps.orcUi.composition.weather.WeatherRadarController")
@patch("apps.orcUi.composition.weather.RadarTileService")
@patch("apps.orcUi.composition.weather.WeatherController")
@patch("apps.orcUi.composition.weather.ServiceRuntimeConfigParser")
def test_weather_composition_defers_optional_bridge_injection_probe(
    parser_class: Mock,
    _weather_controller: Mock,
    _tile_service: Mock,
    _radar_controller: Mock,
    _bridge_client: Mock,
    injection_class: Mock,
    _screen: Mock,
    _screen_controller: Mock,
) -> None:
    config = parser_class.return_value.load.return_value
    config.navigation.gps.simulation.latitude_deg = 42.0
    config.navigation.gps.simulation.longitude_deg = -83.0
    config.environmental.weather_simulation.bridge_url = "http://phone:8766"
    app = Mock()

    composition = configure_weather(app, map_renderer=Mock())

    assert composition.radar_injection is injection_class.return_value
    injection_class.return_value.refresh.assert_not_called()
