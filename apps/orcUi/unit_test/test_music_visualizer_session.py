# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import numpy as np

from apps.orcUi.music_visualizer_session import MusicVisualizerSession
from controllers.audio.music_analysis.music_analysis_session import PushAudioCapture


def test_session_analyzes_pcm_calibrates_and_rejects_stale_callbacks():
    frames = []
    capture = PushAudioCapture()
    session = MusicVisualizerSession(lambda: capture, frames.append)
    assert not session.is_running
    session.start()
    assert session.is_running
    rate = 48_000
    tone = 0.5 * np.sin(2 * np.pi * 1000 * np.arange(2048) / rate)
    capture.push(tone, rate)
    assert len(frames) == 1
    assert frames[0].level > 0
    assert len(frames[0].spectrum) == 24
    session.start_zeroize()
    capture.push(np.zeros(2048), rate)
    session.finish_zeroize()
    assert session.is_zeroized
    session.clear_zeroize()
    assert not session.is_zeroized
    callback = capture._callback
    session.close()
    assert not session.is_running
    count = len(frames)
    callback(tone, rate)
    assert len(frames) == count
