# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Offline weather behavior without a display server."""
from unittest.mock import Mock, patch
from controllers.weather.weather_screen_controller import WeatherScreenController
from frontends.tk.weather.orc_weather_panel import OrcWeatherPanel
from apps.orcUi.frontend.tk.weather_alert_banner import WeatherAlertBanner


def test_offline_refresh_starts_no_worker_and_invalidates_inflight_result():
    host = Mock()
    controller = Mock()
    screen = WeatherScreenController(host, controller, Mock(), online_allowed=lambda: False)
    screen._visible = True
    screen._panel = screen._ui
    screen._presenter = Mock()
    screen._visible = True
    old_generation = screen._generation
    screen.mode_changed(False)
    with patch("controllers.weather.weather_screen_controller.threading.Thread") as worker:
        screen.request_refresh()
        worker.assert_not_called()
    screen._complete(old_generation, Mock(), '')
    screen._presenter.present.assert_not_called()
    screen._panel.set_online.assert_called_once_with(False)


def test_cached_forecast_label_includes_offline_and_full_date():
    panel = OrcWeatherPanel.__new__(OrcWeatherPanel)
    panel._online = False
    # January 3 UTC remains in 1970 in every supported local timezone.
    text = panel._provider_label_text(Mock(provider_label="Open-Meteo", fetched_at=172800.0))
    assert "Offline" in text and "Cached" in text and "1970" in text


def test_offline_alert_label_warns_without_mutating_alert():
    banner = WeatherAlertBanner.__new__(WeatherAlertBanner)
    banner._online = False
    banner._alert = Mock(headline="Storm warning")
    assert "may be outdated" in banner._headline_text()
    assert banner._alert.headline == "Storm warning"
    banner._online = True
    assert banner._headline_text() == "Storm warning"


def test_online_transition_enables_panel_before_starting_forced_refresh():
    host = Mock()
    screen = WeatherScreenController(host, Mock(), Mock(), online_allowed=lambda: True)
    screen._visible = True
    screen._panel = screen._ui
    calls = []
    screen._panel.set_online.side_effect = lambda online: calls.append("enabled")
    screen.request_refresh = Mock(side_effect=lambda **kwargs: calls.append("refresh"))
    screen.mode_changed(True)
    assert calls == ["enabled", "refresh"]
    screen.request_refresh.assert_called_once_with(force=True)


def test_forced_refresh_bypasses_cache_and_reports_error_without_clearing_forecast():
    host = Mock()
    host.schedule_ui_callback.side_effect = lambda delay, callback: callback() if delay == 0 else None
    controller = Mock()
    controller.refresh.side_effect = TimeoutError("forecast timed out")
    from controllers.weather.weather_state import WeatherState, WeatherSource, CurrentWeather
    cached = WeatherState(latitude=0, longitude=0, location_name='Cached', location_source='test',
                          source=WeatherSource('test', 'Test'), fetched_at=100,
                          current=CurrentWeather(temperature_k=283.15))
    screen = WeatherScreenController(host, controller, Mock())
    screen._presenter = Mock()
    screen._visible = True
    screen._last_state = cached
    screen._refresh(screen._generation, force=True)
    controller.refresh.assert_called_once_with()
    controller.refresh_if_stale.assert_not_called()
    screen._presenter.present.assert_not_called()
    assert "showing saved data" in screen._ui.set_weather_status.call_args.args[0]
