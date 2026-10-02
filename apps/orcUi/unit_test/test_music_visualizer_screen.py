# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

from threading import Event
from unittest.mock import Mock

from apps.orcUi.frontend.tk.music_visualizer_screen import MusicVisualizerScreen
from apps.orcUi.music_visualizer_composition import MusicVisualizerSource


def test_audio_frames_are_coalesced_and_stale_generations_are_ignored():
    screen = MusicVisualizerScreen(Mock(), on_back=Mock(), theme_bundle=Mock())
    try:
        for value in range(100):
            screen._offer_frame(screen._generation, value)
        assert screen._frames.qsize() == 1
        assert screen._frames.get_nowait()[1] == 99
        screen._offer_frame(screen._generation - 1, 100)
        assert screen._frames.empty()
    finally:
        screen.close()


def test_navigating_away_during_capture_start_closes_late_session():
    started, release = Event(), Event()
    session = Mock()
    def start():
        started.set()
        assert release.wait(3)
    session.start.side_effect = start
    host = Mock()
    screen = MusicVisualizerScreen(host, on_back=Mock(), theme_bundle=Mock(),
                                   session_factory=lambda callback, source: session)
    try:
        screen._executor.submit(screen._start_capture, screen._generation, MusicVisualizerSource.PIPEWIRE)
        assert started.wait(3)
        screen._poll_job = 'poll'
        screen.hide()
        host.cancel_ui_callback.assert_called_once_with('poll')
        release.set()
    finally:
        release.set()
        screen.close()
    session.close.assert_called_once_with()
    assert screen._session is None


def test_start_failure_releases_backend_and_reports_error():
    session = Mock()
    session.start.side_effect = RuntimeError('bridge consent required')
    screen = MusicVisualizerScreen(Mock(), on_back=Mock(), theme_bundle=Mock(),
                                   session_factory=lambda callback, source: session)
    try:
        screen._start_capture(screen._generation, MusicVisualizerSource.ANDROID_PLAYBACK)
        session.close.assert_called_once_with()
        assert screen._session is None
        assert 'bridge consent required' in screen._messages.get_nowait()[1]
    finally:
        screen.close()
