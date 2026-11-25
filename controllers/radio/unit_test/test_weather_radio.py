# SPDX-License-Identifier: MIT
"""NOAA retry and cancellation policy executes independently of frontend timers."""

from __future__ import annotations

from unittest.mock import Mock
from urllib.request import Request

import pytest

from controllers.radio.weather_radio import play_weather_radio


def test_weather_retries_in_worker_and_returns_station(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_weather_retirement_stops_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    radio, application = Mock(), Mock()
    radio.active_profile_key = "weather_band"
    radio.catalog.profile.return_value.presets = (Mock(),)
    radio.tune_preset.side_effect = RuntimeError("not ready")
    retired = False

    def retire(_delay: float) -> None:
        nonlocal retired
        retired = True

    monkeypatch.setattr("controllers.radio.weather_radio.sleep", retire)
    assert play_weather_radio(radio, application, cancelled=lambda: retired) is None
    radio.tune_preset.assert_called_once()


def test_weather_without_presets_does_not_launch() -> None:
    radio, application = Mock(), Mock()
    radio.catalog.profile.return_value.presets = ()
    with pytest.raises(ValueError, match="presets"):
        play_weather_radio(radio, application, cancelled=lambda: False)
    application.present.assert_not_called()


def test_native_weather_starts_stopped_shared_receiver(monkeypatch: pytest.MonkeyPatch) -> None:
    radio, application = Mock(), Mock()
    radio.active_profile_key = "weather_band"
    radio.catalog.profile.return_value.key = "weather_band"
    radio.catalog.profile.return_value.presets = (Mock(),)
    station = Mock()
    radio.tune_preset.return_value = station
    calls: list[str | Request] = []

    class Response:
        status = 202

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return (
                b'{"running": true, "starting": false}'
                if len(calls) >= 3
                else b'{"running": false, "starting": false}'
            )

    def urlopen(request: str | Request, timeout: float) -> Response:
        calls.append(request)
        return Response()

    monkeypatch.setattr("controllers.radio.weather_radio.urllib.request.urlopen", urlopen)
    monkeypatch.setattr("controllers.radio.weather_radio.sleep", Mock())
    assert (
        play_weather_radio(radio, application, cancelled=lambda: False, native_sdrforge=True)
        is station
    )
    assert len(calls) == 3
    assert calls[0] == "http://127.0.0.1:5570/v1/receiver"
    assert isinstance(calls[1], Request)
    assert calls[1].get_method() == "POST"
    assert calls[1].full_url.endswith("/v1/receiver/start")
    assert calls[2] == "http://127.0.0.1:5570/v1/receiver"


@pytest.mark.parametrize(
    "status",
    [
        b'{"running": true, "starting": false}',
        b'{"running": false, "starting": true}',
    ],
)
def test_native_weather_does_not_restart_active_receiver(monkeypatch: pytest.MonkeyPatch, status: bytes) -> None:
    radio, application = Mock(), Mock()
    radio.active_profile_key = "weather_band"
    radio.catalog.profile.return_value.key = "weather_band"
    radio.catalog.profile.return_value.presets = (Mock(),)
    calls: list[str | Request] = []

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return status if len(calls) == 1 else b'{"running": true, "starting": false}'

    def urlopen(request: str | Request, timeout: float) -> Response:
        calls.append(request)
        return Response()

    monkeypatch.setattr("controllers.radio.weather_radio.urllib.request.urlopen", urlopen)
    play_weather_radio(radio, application, cancelled=lambda: False, native_sdrforge=True)
    assert len(calls) == (2 if b'"starting": true' in status else 1)


def test_native_weather_surfaces_rest_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    radio, application = Mock(), Mock()
    radio.active_profile_key = "weather_band"
    radio.catalog.profile.return_value.key = "weather_band"
    radio.catalog.profile.return_value.presets = (Mock(),)
    monkeypatch.setattr(
        "controllers.radio.weather_radio._ensure_native_receiver_started",
        Mock(side_effect=RuntimeError("SDRForge unavailable")),
    )
    monkeypatch.setattr("controllers.radio.weather_radio.sleep", Mock())
    with pytest.raises(RuntimeError, match="SDRForge unavailable"):
        play_weather_radio(radio, application, cancelled=lambda: False, native_sdrforge=True)


def test_native_weather_reports_async_startup_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    radio, application = Mock(), Mock()
    radio.active_profile_key = "weather_band"
    radio.catalog.profile.return_value.key = "weather_band"
    radio.catalog.profile.return_value.presets = (Mock(),)
    calls: list[str | Request] = []

    class Response:
        status = 202

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            if len(calls) >= 3:
                return b'{"running": false, "starting": false, "startup_error": "USB disconnected"}'
            return b'{"running": false, "starting": false}'

    def urlopen(request: str | Request, timeout: float) -> Response:
        calls.append(request)
        return Response()

    monkeypatch.setattr("controllers.radio.weather_radio.urllib.request.urlopen", urlopen)
    monkeypatch.setattr("controllers.radio.weather_radio.sleep", Mock())
    with pytest.raises(RuntimeError, match="USB disconnected"):
        play_weather_radio(radio, application, cancelled=lambda: False, native_sdrforge=True)


def test_native_startup_failure_does_not_retune_or_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    radio, application = Mock(), Mock()
    radio.active_profile_key = "weather_band"
    radio.catalog.profile.return_value.key = "weather_band"
    radio.catalog.profile.return_value.presets = (Mock(),)
    start = Mock(side_effect=RuntimeError("USB disconnected"))
    pause = Mock()
    monkeypatch.setattr("controllers.radio.weather_radio._ensure_native_receiver_started", start)
    monkeypatch.setattr("controllers.radio.weather_radio.sleep", pause)

    with pytest.raises(RuntimeError, match="USB disconnected"):
        play_weather_radio(radio, application, cancelled=lambda: False, native_sdrforge=True)
    radio.tune_preset.assert_called_once()
    start.assert_called_once()
    pause.assert_not_called()


def test_native_cancelled_during_startup_does_not_claim_playing(monkeypatch: pytest.MonkeyPatch) -> None:
    radio, application = Mock(), Mock()
    radio.active_profile_key = "weather_band"
    radio.catalog.profile.return_value.key = "weather_band"
    radio.catalog.profile.return_value.presets = (Mock(),)
    monkeypatch.setattr(
        "controllers.radio.weather_radio._ensure_native_receiver_started",
        Mock(return_value=False),
    )
    assert (
        play_weather_radio(radio, application, cancelled=lambda: False, native_sdrforge=True)
        is None
    )
