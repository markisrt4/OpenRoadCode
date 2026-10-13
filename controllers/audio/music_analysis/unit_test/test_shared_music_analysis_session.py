# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
from unittest.mock import Mock, patch

import pytest

from controllers.audio.music_analysis.music_analysis_session import PushAudioCapture
from controllers.audio.music_analysis.shared_music_analysis_session import SharedMusicAnalysisSession


@pytest.fixture
def shared():
    capture = PushAudioCapture()
    now = [10.0]
    session = SharedMusicAnalysisSession({'android-playback': lambda: capture}, clock=lambda: now[0])
    with patch('controllers.audio.music_analysis.shared_music_analysis_session.Timer') as timer:
        yield session, capture, now, timer
    session.close()


def test_home_never_starts_capture(shared):
    session, capture, _, _ = shared
    session.select('android-playback')
    session.attach_home()
    assert not capture.is_running
    assert not session.read_spectrum().active


def test_browser_to_home_handoff_preserves_one_capture(shared):
    session, capture, _, timer = shared
    session.attach_browser()
    session.start('android-playback')
    session.detach_browser()
    pending = session._release_generation
    session.attach_home()
    session._stop_if_idle(pending)
    assert capture.is_running
    timer.return_value.cancel.assert_called()
    session.detach_home()
    session._stop_if_idle(session._release_generation)
    assert not capture.is_running
    session.attach_home()
    assert not capture.is_running  # Reopening Home does not restart capture.


def test_real_frames_expire_and_source_specific_browser_stop_is_ignored(shared):
    session, capture, now, _ = shared
    session.start('android-playback')
    capture.push([0.2] * 2048, 48000)
    state = session.read_spectrum()
    assert state.active and state.bands
    assert all(0 <= band <= 1 for band in state.bands)
    session.stop(source='browser')
    assert capture.is_running and session.read_spectrum().active
    now[0] += 1
    assert not session.read_spectrum().active
    session.stop()
    assert not session.read_spectrum().active


def test_closed_or_old_capture_cannot_republish(shared):
    session, capture, _, _ = shared
    session.start('android-playback')
    old = session._generation
    session.stop()
    session.start()
    session._on_samples(old, [0.2] * 2048, 48000)
    assert not session.read_spectrum().active
    session.close()
    session.close()
    session._on_samples(session._generation, [0.2] * 2048, 48000)
    assert not capture.is_running and not session.read_spectrum().active
    with pytest.raises(RuntimeError, match='closed'):
        session.start()


def test_leaving_both_views_does_not_stop_on_tk_thread(shared):
    session, capture, _, timer = shared
    session.attach_home()
    session.start('android-playback')
    session.detach_home()
    assert capture.is_running
    timer.assert_called_once()
    assert timer.return_value.daemon
    timer.return_value.start.assert_called_once()
