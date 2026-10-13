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


def test_capture_lifecycle_reports_pending_running_natural_stop_and_explicit_stop():
    from ui.music_visualizer.music_visualizer_types import MusicCaptureState
    entered, release = Event(), Event()
    session = Mock(is_running=True)

    def start():
        entered.set()
        assert release.wait(3)

    session.start.side_effect = start
    controller = MusicVisualizerController(lambda callback, source: session)
    try:
        assert controller.capture_state() is MusicCaptureState.IDLE
        controller.start(MusicVisualizerSource.ANDROID_PLAYBACK)
        assert entered.wait(3)
        assert controller.capture_state() is MusicCaptureState.STARTING
        release.set()
        controller._executor.submit(lambda: None).result(timeout=3)
        assert controller.capture_state() is MusicCaptureState.RUNNING
        session.is_running = False
        assert controller.capture_state() is MusicCaptureState.IDLE
        controller.stop()
        assert controller.capture_state() is MusicCaptureState.IDLE
    finally:
        release.set()
        controller.close()


def test_capture_failure_and_simulation_have_explicit_lifecycle_states():
    from ui.music_visualizer.music_visualizer_types import MusicCaptureState
    controller = MusicVisualizerController(Mock(side_effect=RuntimeError('unavailable')))
    try:
        controller.start(MusicVisualizerSource.ANDROID_PLAYBACK)
        controller._executor.submit(lambda: None).result(timeout=3)
        assert controller.capture_state() is MusicCaptureState.IDLE
    finally:
        controller.close()
    simulation = MusicVisualizerController(lambda callback, source: None)
    try:
        simulation.start(MusicVisualizerSource.SIMULATED)
        simulation._executor.submit(lambda: None).result(timeout=3)
        assert simulation.capture_state() is MusicCaptureState.RUNNING
        simulation.stop()
        assert simulation.capture_state() is MusicCaptureState.IDLE
    finally:
        simulation.close()
