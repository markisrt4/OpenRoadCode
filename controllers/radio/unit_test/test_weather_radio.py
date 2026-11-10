# SPDX-License-Identifier: MIT
"""NOAA retry and cancellation policy executes independently of frontend timers."""
from unittest.mock import Mock

import pytest

from controllers.radio.weather_radio import play_weather_radio


def test_weather_retries_in_worker_and_returns_station(monkeypatch):
    radio, application = Mock(), Mock()
    radio.active_profile_key = "weather_band"
    radio.catalog.profile.return_value.key = "weather_band"
    radio.catalog.profile.return_value.presets = (Mock(),)
    state = Mock()
    radio.tune_preset.side_effect = [RuntimeError("not ready"), state]
    pause = Mock()
    monkeypatch.setattr("controllers.radio.weather_radio.sleep", pause)
    assert play_weather_radio(radio, application, cancelled=lambda: False) is state
    pause.assert_called_once_with(0.25)
    application.present.assert_called_once()


def test_weather_retirement_stops_retries(monkeypatch):
    radio, application = Mock(), Mock()
    radio.active_profile_key = "weather_band"
    radio.catalog.profile.return_value.presets = (Mock(),)
    radio.tune_preset.side_effect = RuntimeError("not ready")
    retired = False
    def retire(_delay):
        nonlocal retired
        retired = True
    monkeypatch.setattr("controllers.radio.weather_radio.sleep", retire)
    assert play_weather_radio(radio, application, cancelled=lambda: retired) is None
    radio.tune_preset.assert_called_once()


def test_weather_without_presets_does_not_launch():
    radio, application = Mock(), Mock()
    radio.catalog.profile.return_value.presets = ()
    with pytest.raises(ValueError, match="presets"):
        play_weather_radio(radio, application, cancelled=lambda: False)
    application.present.assert_not_called()
