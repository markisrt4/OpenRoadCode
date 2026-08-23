# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import math

from controllers.audio_analysis.music_analysis import MusicAnalyzer
from hardware_io.audio.audio_capture_if import AudioFrame


def _music_frame() -> AudioFrame:
    sample_rate=48_000
    samples=tuple(
        .08*math.sin(2*math.pi*80*i/sample_rate)
        +.04*math.sin(2*math.pi*1_000*i/sample_rate)
        +.02*math.sin(2*math.pi*8_000*i/sample_rate)
        for i in range(2048)
    )
    return AudioFrame(samples,sample_rate)


def test_sensitivity_scales_complete_visual_analysis_state() -> None:
    quiet=MusicAnalyzer();quiet.set_sensitivity(.5)
    strong=MusicAnalyzer();strong.set_sensitivity(1.5)

    quiet_audio=quiet.analyze(_music_frame()).audio
    strong_audio=strong.analyze(_music_frame()).audio

    assert strong_audio.level>quiet_audio.level
    assert strong_audio.peak>quiet_audio.peak
    assert strong_audio.bass>quiet_audio.bass
    assert strong_audio.mid>quiet_audio.mid
    assert strong_audio.treble>quiet_audio.treble
    assert sum(strong_audio.spectrum)>sum(quiet_audio.spectrum)
