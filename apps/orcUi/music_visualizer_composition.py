# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose ORC music visualizer analysis sources."""

from __future__ import annotations

import os
from collections.abc import Callable
from enum import Enum

from apps.orcUi.music_visualizer_panel import VisualizerFrame
from apps.orcUi.music_visualizer_session import MusicVisualizerSession
from controllers.audio.capture import PipewireAudioCapture
from controllers.audio.music_analysis import MusicAnalysisPipeline, MusicAnalyzer


class MusicVisualizerSource(str, Enum):
    """Supported ORC music visualizer input sources."""

    SIMULATED = "simulated"
    PIPEWIRE = "pipewire"


def selected_music_visualizer_source() -> MusicVisualizerSource:
    """Return the configured visualizer source.

    The simulated source remains the safe default so Android/Termux does not
    accidentally try to start a PipeWire backend that is unavailable there.
    """
    raw = os.getenv("OPENROAD_MUSIC_VISUALIZER_SOURCE", MusicVisualizerSource.SIMULATED.value)
    try:
        return MusicVisualizerSource(raw.strip().lower())
    except ValueError as exc:
        supported = ", ".join(source.value for source in MusicVisualizerSource)
        raise ValueError(
            f"Unsupported OPENROAD_MUSIC_VISUALIZER_SOURCE '{raw}'; expected one of: {supported}"
        ) from exc


def _pipewire_block_size() -> int:
    """Return the configured PipeWire capture block size."""
    raw = os.getenv("OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE", "2048")
    try:
        block_size = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE must be an integer, got '{raw}'"
        ) from exc
    if block_size < 2048:
        raise ValueError("OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE must be >= 2048")
    return block_size


def create_music_visualizer_session(
    callback: Callable[[VisualizerFrame], None],
    *,
    source: MusicVisualizerSource | None = None,
) -> MusicVisualizerSession | None:
    """Create the selected real-audio session, or None for simulation."""
    selected = source or selected_music_visualizer_source()
    if selected is MusicVisualizerSource.SIMULATED:
        return None

    target = os.getenv("OPENROAD_MUSIC_VISUALIZER_PIPEWIRE_TARGET") or None
    block_size = _pipewire_block_size()

    def pipeline_factory(analysis_callback):
        return MusicAnalysisPipeline(
            PipewireAudioCapture(target=target, block_size=block_size),
            MusicAnalyzer(),
            analysis_callback,
        )

    return MusicVisualizerSession(pipeline_factory, callback)
