# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from apps.orcUi.adapters.native_home_spectrum_feed import NativeHomeSpectrumFeed
from ui.music_visualizer import MusicVisualizerSource, VisualizerFrame
from ui.music_visualizer.music_visualizer_types import MusicCaptureState


def test_feed_adapts_cached_native_frames_and_expires_stale_bands():
    controller = Mock()
    controller.latest_frame.return_value = VisualizerFrame(
        level=0.5, bass=0.4, mid=0.3, treble=0.2, spectrum=(0.1, 0.8)
    )
    controller.capture_state.return_value = MusicCaptureState.RUNNING
    now = [10.0]
    feed = NativeHomeSpectrumFeed(
        controller,
        default_source=MusicVisualizerSource.PIPEWIRE,
        clock=lambda: now[0],
    )

    assert feed.read_spectrum().bands == (0.1, 0.8)
    now[0] = 11.0
    state = feed.read_spectrum()
    assert state.bands == ()
    assert not state.active
    assert state.running


def test_feed_delegates_visibility_and_explicit_capture_requests():
    controller = Mock()
    controller.selected_source.return_value = None
    feed = NativeHomeSpectrumFeed(
        controller,
        default_source=MusicVisualizerSource.PIPEWIRE,
    )

    feed.attach_home()
    feed.attach_home()
    feed.request_start_spectrum()
    feed.request_stop_spectrum()
    feed.detach_home()
    feed.detach_home()

    controller.attach_view.assert_called_once()
    controller.start.assert_called_once_with(MusicVisualizerSource.PIPEWIRE)
    controller.stop.assert_called_once_with()
    controller.detach_view.assert_called_once()
