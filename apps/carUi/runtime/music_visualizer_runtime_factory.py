# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Composition root for Car UI music-visualizer services."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from controllers.audio_analysis.music_analysis import MusicAnalyzer
from controllers.audio_analysis.music_analysis_source_if import MusicAnalysisSourceIf
from controllers.audio_analysis.pcm_music_analysis_source import PcmMusicAnalysisSource
from controllers.cache.persistent_cache import PersistentCache
from controllers.music_lighting import MusicLightingController
from controllers.song_recognition import (
    AcrCloudConfig,
    AcrCloudSongRecognizer,
    SongMetadataCache,
    SongRecognitionController,
    SongRecognitionIf,
    UnconfiguredSongRecognizer,
)
from hardware_io.audio.pipewire_audio_capture import PipeWireAudioCapture


@dataclass(frozen=True, slots=True)
class MusicVisualizerRuntime:
    analysis_source: MusicAnalysisSourceIf
    song_recognition: SongRecognitionController
    music_lighting: MusicLightingController

    def close(self) -> None:
        self.analysis_source.stop()


def create_music_visualizer_runtime() -> MusicVisualizerRuntime:
    """Build the platform/provider-specific services used by Car UI."""
    source = PcmMusicAnalysisSource(
        capture=PipeWireAudioCapture(),
        analyzer=MusicAnalyzer(spectrum_band_count=24),
    )
    host = os.environ.get("ACRCLOUD_HOST", "").strip()
    key = os.environ.get("ACRCLOUD_ACCESS_KEY", "").strip()
    secret = os.environ.get("ACRCLOUD_ACCESS_SECRET", "").strip()
    recognizer: SongRecognitionIf = (
        AcrCloudSongRecognizer(AcrCloudConfig(host, key, secret))
        if host and key and secret
        else UnconfiguredSongRecognizer()
    )
    metadata_cache = SongMetadataCache(
        PersistentCache(
            Path("~/.cache/openroadcode/song_recognition").expanduser(),
            suffix=".json",
        )
    )
    return MusicVisualizerRuntime(
        analysis_source=source,
        song_recognition=SongRecognitionController(source, recognizer, metadata_cache),
        music_lighting=MusicLightingController(),
    )
