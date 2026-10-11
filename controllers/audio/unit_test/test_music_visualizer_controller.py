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


def test_home_and_full_visualizer_share_one_capture_and_preferences():
    from ui.music_visualizer import VisualizerFrame
    from ui.music_visualizer.music_visualizer_types import MusicVisualizerOptions, MusicVisualizationMode
    released = Event()
    session = Mock()
    session.is_running = True
    session.close.side_effect = released.set
    factory = Mock(return_value=session)
    controller = MusicVisualizerController(factory)
    try:
        controller.attach_view('full')
        controller.start(MusicVisualizerSource.ANDROID_PLAYBACK)
        controller._executor.submit(lambda: None).result(timeout=2)
        controller.start(MusicVisualizerSource.ANDROID_PLAYBACK)
        controller._executor.submit(lambda: None).result(timeout=2)
        assert factory.call_count == 1
        frame = VisualizerFrame(.3, .2, .1, .1, (.2,)*24)
        controller._offer_frame(controller._generation, frame)
        assert controller.latest_frame() is frame
        assert controller.latest_frame() is frame
        assert controller.presentation()[0] is frame
        assert controller.latest_frame() is frame
        options = MusicVisualizerOptions(mode=MusicVisualizationMode.NEON_RIBBON, drum_gain=.4)
        controller.configure_visualizer(options)
        controller.set_home_visualizer_enabled(True)
        controller.detach_view('full')
        controller.attach_view('home')
        assert not released.wait(.35)
        assert controller.visualizer_options() is options
        assert controller.home_visualizer_enabled()
        assert controller.selected_source() is MusicVisualizerSource.ANDROID_PLAYBACK
        controller.detach_view('home')
        assert released.wait(2)
        assert controller.latest_frame() is None
    finally:
        controller.close()


def test_close_cancels_navigation_handoff_and_ignores_late_audio():
    controller = MusicVisualizerController(Mock())
    controller.attach_view('home')
    controller.detach_view('home')
    controller.close()
    controller._offer_frame(controller._generation - 1, Mock())
    assert controller.latest_frame() is None
    assert controller._detach_timer is None
