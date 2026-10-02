# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
from threading import Event
from unittest.mock import Mock

from controllers.audio.music_analysis.music_visualizer_controller import MusicVisualizerController
from ui.music_visualizer import MusicVisualizerSource


def test_audio_frames_are_coalesced_and_stale_generations_are_ignored():
    controller = MusicVisualizerController(Mock())
    try:
        for value in range(100):
            controller._offer_frame(controller._generation, value)
        assert controller.presentation()[0] == 99
        controller._offer_frame(controller._generation - 1, 100)
        assert controller.presentation()[0] is None
    finally:
        controller.close()


def test_stopping_during_capture_start_closes_late_session():
    started, release = Event(), Event()
    session = Mock()
    def start():
        started.set()
        assert release.wait(3)
    session.start.side_effect = start
    controller = MusicVisualizerController(lambda callback, source: session)
    try:
        controller.start(MusicVisualizerSource.PIPEWIRE)
        assert started.wait(3)
        controller.stop()
        release.set()
    finally:
        release.set()
        controller.close()
    session.close.assert_called_once_with()
    assert controller._session is None
    assert controller.presentation() == (None, None)


def test_start_failure_releases_backend_and_reports_error():
    session = Mock()
    session.start.side_effect = RuntimeError('bridge consent required')
    controller = MusicVisualizerController(lambda callback, source: session)
    try:
        controller._start_capture(controller._generation, MusicVisualizerSource.ANDROID_PLAYBACK)
        session.close.assert_called_once_with()
        assert controller._session is None
        assert 'bridge consent required' in controller.presentation()[1]
    finally:
        controller.close()
