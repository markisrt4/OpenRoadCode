# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""The gate must reject real weather boundary violations and accept UI-only views."""

from scripts.check_weather_ui_contracts import check_frontend


def test_provider_import_and_transport_alias_cannot_bypass_the_gate():
    for source in ('from controllers.weather.city_weather import CityWeatherProvider',
                   'import protocols.map_renderer.map_renderer_client as transport',
                   'import requests as http', 'from threading import Thread',
                   'from apps.orcUi.composition.weather_overlays import configure_weather_overlays'):
        assert check_frontend('view.py', source)


def test_ui_contract_imports_and_local_widget_state_are_allowed():
    source = '''from ui.weather.weather_overlay_state import CityWeatherOverlayState
from ui.weather.weather_overlay_request_handler_if import WeatherOverlayRequestHandlerIf
class View:
    def render(self):
        return self._city_state.hours
'''
    assert check_frontend('view.py', source) == []


def test_inspecting_controller_cache_or_using_renderer_is_rejected():
    for attribute in ('_provider', '_renderer', '_weather', '_cities', '_radar_controller'):
        assert check_frontend('view.py', f'return_value = controller.{attribute}')
