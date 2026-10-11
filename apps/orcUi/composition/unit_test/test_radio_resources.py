# SPDX-License-Identifier: MIT

"""Radio composition owns workers, sessions, subscriptions, and rollback."""

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from apps.orcUi.composition.radio import StreamingRadioResources, configure_radio
from ui.theme import ThemeMode


def test_close_attempts_all_resources_and_is_idempotent():
    cancel, executor, unsubscribe = Mock(), Mock(spec=ThreadPoolExecutor), Mock()
    session = Mock()
    resources = StreamingRadioResources(cancel, executor=executor)
    resources.sessions.add(session)
    resources.unsubscribe = unsubscribe
    resources.adsb_callback = "adsb-timer"
    unsubscribe.side_effect = RuntimeError("unsubscribe failed")
    with pytest.raises(RuntimeError, match="unsubscribe failed"):
        resources.close()
    cancel.assert_called_once_with("adsb-timer")
    session.close.assert_called_once()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    resources.close()
    resources.run_work(Mock())
    executor.submit.assert_not_called()


def test_failed_registration_rolls_back_workers_and_listener(monkeypatch):
    executor, artwork_executor = Mock(spec=ThreadPoolExecutor), Mock(spec=ThreadPoolExecutor)
    rf_executor = Mock(spec=ThreadPoolExecutor)
    pools = iter((executor, artwork_executor, rf_executor))
    monkeypatch.setattr("apps.orcUi.composition.radio.ThreadPoolExecutor", lambda **k: next(pools))
    monkeypatch.setattr("apps.orcUi.composition.radio.RadioBrowserDirectory", Mock())
    monkeypatch.setattr("apps.orcUi.composition.radio.StreamingRadioFavorites", Mock())
    monkeypatch.setattr("apps.orcUi.composition.radio.OrcUiAdsbControl", Mock())
    monkeypatch.setattr("apps.orcUi.composition.radio.RadioScreen", Mock())
    app = Mock()
    app.theme_mode = ThemeMode.DARK
    app.register_screen.side_effect = ValueError("registration failed")
    unsubscribe = app.online_mode.subscribe.return_value
    with pytest.raises(ValueError, match="registration failed"):
        configure_radio(app, Mock())
    unsubscribe.assert_called_once()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    artwork_executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)


def test_panel_factory_owns_session_and_rolls_it_back_on_widget_failure(monkeypatch):
    executor = Mock(spec=ThreadPoolExecutor)
    monkeypatch.setattr("apps.orcUi.composition.radio.ThreadPoolExecutor", lambda **k: executor)
    for name in ("RadioBrowserDirectory", "StreamingRadioFavorites", "OrcUiAdsbControl"):
        monkeypatch.setattr(f"apps.orcUi.composition.radio.{name}", Mock())
    screen_type = Mock()
    monkeypatch.setattr("apps.orcUi.composition.radio.RadioScreen", screen_type)
    entry_type = Mock()
    monkeypatch.setattr("apps.orcUi.composition.radio.RadioEntryPanel", entry_type)
    session = Mock()
    monkeypatch.setattr("apps.orcUi.composition.radio.StreamingRadioBrowser", Mock(return_value=session))
    monkeypatch.setattr("apps.orcUi.composition.radio.PersistentStreamingRadioPanel", Mock(side_effect=ValueError("widget failed")))
    app = Mock()
    app.theme_mode = ThemeMode.DARK
    composition = configure_radio(app, Mock())
    screen_type.call_args.kwargs["panel_factory"](Mock(), Mock())
    factory = entry_type.call_args.kwargs["streaming_panel_factory"]
    with pytest.raises(ValueError, match="widget failed"):
        factory(Mock(), Mock(), Mock())
    session.close.assert_called_once()
    assert not composition.streaming_resources.sessions
    composition.close()


def test_artwork_scheduler_is_separate_from_playback_workers():
    executor, artwork = Mock(spec=ThreadPoolExecutor), Mock(spec=ThreadPoolExecutor)
    resources = StreamingRadioResources(Mock(), executor=executor, artwork_executor=artwork)
    playback_work, image_work = Mock(), Mock()
    resources.run_work(playback_work)
    resources.run_artwork(image_work)
    executor.submit.assert_called_once_with(playback_work)
    artwork.submit.assert_called_once_with(image_work)
    resources.close()
    artwork.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
