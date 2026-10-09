# SPDX-License-Identifier: MIT

"""Policy marking adds no toolkit, constructor or lifecycle obligations."""

from frontends.tk.tk_screen import TkScreen
from frontends.tk.weather.orc_weather_panel import OrcWeatherPanel
from ui import ScreenUiIf, UiWidget


def test_screen_policy_is_inherited_and_panels_can_opt_in_independently():
    assert issubclass(ScreenUiIf, UiWidget)
    assert issubclass(TkScreen, UiWidget)
    assert issubclass(OrcWeatherPanel, UiWidget)


def test_marker_does_not_change_widget_constructor_or_require_screen_lifecycle():
    class Panel(UiWidget):
        def __init__(self, request_handler):
            self.request_handler = request_handler

    supplied_contract = object()
    panel = Panel(supplied_contract)
    assert panel.request_handler is supplied_contract
    assert not hasattr(panel, 'show')
    assert not hasattr(panel, 'hide')
    assert '__init__' not in UiWidget.__dict__
