# SPDX-License-Identifier: MIT

from unittest.mock import Mock, patch

import pytest

from apps.orcUi.composition.radio import configure_radio
from frontends.tk.weather.orc_weather_panel import OrcWeatherPanel
from ui.radio.radio_profile_state import RadioProfileState
from ui.theme import ThemeMode


@pytest.fixture
def action():
    app, runtime, resources = Mock(), Mock(), Mock()
    app.theme_mode = ThemeMode.DARK
    resources.closed = False
    work, deliveries = [], []
    resources.run_rf.side_effect = work.append
    app.dispatch_ui.side_effect = deliveries.append
    with patch("apps.orcUi.composition.radio.StreamingRadioResources", return_value=resources), patch(
        "apps.orcUi.composition.radio.RadioScreen"), patch(
        "apps.orcUi.composition.radio.RadioBrowserDirectory"), patch(
        "apps.orcUi.composition.radio.StreamingRadioFavorites"):
        composition = configure_radio(app, runtime)
    return composition.open_weather_radio, app, runtime, resources, work, deliveries


def test_button_emits_wired_action(caplog):
    panel = object.__new__(OrcWeatherPanel)
    panel._on_weather_radio = Mock()
    with caplog.at_level("INFO", logger="orc.radio.noaa"):
        panel._request_weather_radio()
    panel._on_weather_radio.assert_called_once_with()
    assert "NOAA button pressed" in caplog.text


def test_noaa_action_queues_work_and_delivery(action, caplog):
    request, app, runtime, _, work, deliveries = action
    state = RadioProfileState("WX1", 162550000, "NFM", "weather_band", "Weather Band")
    with patch("apps.orcUi.composition.radio.RadioProfileController") as radio, patch(
        "apps.orcUi.composition.radio.play_weather_radio", return_value=state) as tune, caplog.at_level("INFO", logger="orc.radio.noaa"):
        request()
        tune.assert_not_called()
        work.pop(0)()
        tune.assert_called_once_with(radio.return_value, runtime.radio, cancelled=tune.call_args.kwargs["cancelled"])
        assert "NOAA worker started" in caplog.text
        assert "NOAA tuned" in caplog.text
    deliveries.pop(0)()
    assert "162.550" in app.set_screen_status.call_args.args[0]
    app.navigate_to.assert_not_called()


def test_unexpected_worker_failure_is_logged_and_delivered(action, caplog):
    request, app, _, _, work, deliveries = action
    with patch("apps.orcUi.composition.radio.RadioProfileController", side_effect=AttributeError("startup failed")):
        request()
        work.pop(0)()
    assert "NOAA request failed" in caplog.text
    deliveries.pop(0)()
    app.set_screen_status.assert_called_with("RF: startup failed")


def test_retirement_drops_queued_noaa_work(action):
    request, _, _, resources, work, deliveries = action
    request()
    resources.closed = True
    with patch("apps.orcUi.composition.radio.play_weather_radio") as tune:
        work.pop(0)()
    tune.assert_not_called()
    assert not deliveries


def test_retirement_drops_completed_noaa_status(action):
    request, app, _, resources, work, deliveries = action
    state = RadioProfileState("WX1", 162550000, "NFM", "weather_band", "Weather Band")
    with patch("apps.orcUi.composition.radio.RadioProfileController"), patch(
        "apps.orcUi.composition.radio.play_weather_radio", return_value=state):
        request()
        work.pop(0)()
    resources.closed = True
    app.set_screen_status.reset_mock()
    deliveries.pop(0)()
    app.set_screen_status.assert_not_called()
