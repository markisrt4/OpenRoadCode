# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Onset response must decay on sustained music and retrigger on a new hit."""
import numpy as np
from controllers.audio.music_analysis.music_analyzer import MusicAnalyzer
from controllers.audio.music_analysis.music_visualizer_session import MusicVisualizerSession


def test_beat_attacks_decays_and_retriggers_without_silence_pulses():
    analyzer = MusicAnalyzer()
    quiet = np.zeros(2048)
    tone = .5 * np.sin(np.arange(2048) * 2 * np.pi * 70 / 48000)
    assert analyzer.analyze(quiet, 48000).beat == 0
    attack = analyzer.analyze(tone, 48000)
    assert attack.beat > .8
    sustained = [analyzer.analyze(tone, 48000).beat for _ in range(12)]
    assert all(a > b for a,b in zip([attack.beat]+sustained, sustained))
    assert sustained[-1] < .05
    for _ in range(5):
        analyzer.analyze(quiet, 48000)
    assert analyzer.analyze(tone, 48000).beat > .8
    analyzer.clear_zeroize()
    assert analyzer.analyze(quiet, 48000).beat == 0


def test_native_presentation_preserves_onsets_and_percussion():
    analyzer = MusicAnalyzer()
    analyzer.analyze(np.zeros(2048), 48000)
    state = analyzer.analyze(.5*np.sin(np.arange(2048)*2*np.pi*70/48000), 48000)
    frame = MusicVisualizerSession.to_visualizer_frame(state)
    assert frame.beat == state.beat
    assert frame.kick == state.percussion.kick
    assert frame.snare == state.percussion.snare
    assert frame.cymbal == state.percussion.cymbal
