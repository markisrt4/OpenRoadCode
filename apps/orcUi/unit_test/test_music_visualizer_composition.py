# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import pytest

from apps.orcUi.music_visualizer_composition import (
    MusicVisualizerSource,
    create_music_visualizer_session,
    selected_music_visualizer_source,
)


def test_visualizer_source_defaults_to_simulated(monkeypatch):
    monkeypatch.delenv("OPENROAD_MUSIC_VISUALIZER_SOURCE", raising=False)
    assert selected_music_visualizer_source() is MusicVisualizerSource.SIMULATED


def test_simulated_source_requires_no_real_audio_session():
    assert create_music_visualizer_session(
        lambda _frame: None,
        source=MusicVisualizerSource.SIMULATED,
    ) is None


def test_invalid_visualizer_source_is_rejected(monkeypatch):
    monkeypatch.setenv("OPENROAD_MUSIC_VISUALIZER_SOURCE", "cassette-deck")
    with pytest.raises(ValueError, match="OPENROAD_MUSIC_VISUALIZER_SOURCE"):
        selected_music_visualizer_source()


def test_android_source_uses_shared_session_and_android_capture(monkeypatch):
    import apps.orcUi.music_visualizer_composition as composition
    from controllers.audio.music_analysis.music_analysis_session import PushAudioCapture
    capture = PushAudioCapture()
    sizes = []
    def android_capture(*, block_size):
        sizes.append(block_size)
        return capture
    monkeypatch.setattr(composition, 'AndroidPlaybackAudioCapture', android_capture)
    monkeypatch.setenv('OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE', '4096')
    session = create_music_visualizer_session(lambda frame: None,
                                             source=MusicVisualizerSource.ANDROID_PLAYBACK)
    try:
        session.start()
        assert session.is_running
        assert sizes == [4096]
    finally:
        session.close()
    assert not capture.is_running


def test_real_capture_rejects_incomplete_fft_blocks(monkeypatch):
    monkeypatch.setenv('OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE', '512')
    with pytest.raises(ValueError, match='>= 2048'):
        create_music_visualizer_session(lambda frame: None, source=MusicVisualizerSource.PIPEWIRE)
