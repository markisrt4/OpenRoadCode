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
