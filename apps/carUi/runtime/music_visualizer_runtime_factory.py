# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Composition root for Car UI music-visualizer services."""
from __future__ import annotations

import os
from dataclasses import replace
from dataclasses import dataclass
from pathlib import Path

from controllers.audio_analysis.music_analysis_source_if import MusicAnalysisSourceIf
from controllers.audio_analysis.selectable_music_analysis_source import MusicAudioInput, SelectableMusicAnalysisSource
from controllers.cache.persistent_cache import PersistentCache
from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.music_lighting import MusicLightingController, MusicLightingOutputAdapter
from controllers.song_recognition import (
    AcrCloudConfig,
    AcrCloudSongRecognizer,
    SongMetadataCache,
    SongRecognitionController,
    SongRecognitionIf,
    UnconfiguredSongRecognizer,
)
from controllers.spotify import SpotifyControllerIf
from hardware_io.audio.pipewire_audio_capture import PipeWireAudioCapture
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager


@dataclass(frozen=True, slots=True)
class MusicVisualizerRuntime:
    analysis_source: MusicAnalysisSourceIf
    song_recognition: SongRecognitionController
    music_lighting: MusicLightingController
    lighting_output: MusicLightingOutputAdapter | None = None

    def close(self) -> None:
        self.analysis_source.stop()
        if self.lighting_output is not None:
            self.lighting_output.close()


def create_music_visualizer_runtime(
    lighting_controller: LightingControllerIf | None = None,
    spotify_controller: SpotifyControllerIf | None = None,
) -> MusicVisualizerRuntime:
    """Build the platform/provider-specific services used by Car UI."""
    system_device=os.environ.get("CARUI_VISUALIZER_AUDIO_DEVICE","@DEFAULT_MONITOR@")
    external_device=os.environ.get("CARUI_VISUALIZER_EXTERNAL_DEVICE","@DEFAULT_SOURCE@")
    initial_input=MusicAudioInput(os.environ.get("CARUI_VISUALIZER_INPUT",MusicAudioInput.SYSTEM_AUDIO.value))
    source=SelectableMusicAnalysisSource({
        MusicAudioInput.SYSTEM_AUDIO:lambda:PipeWireAudioCapture(device=system_device),
        MusicAudioInput.EXTERNAL_INPUT:lambda:PipeWireAudioCapture(device=external_device),
    },initial_input=initial_input)
    secrets = EnvironmentVariableSecretManager()
    host = secrets.get_secret("ACRCLOUD_HOST") or ""
    key = secrets.get_secret("ACRCLOUD_ACCESS_KEY") or ""
    secret = secrets.get_secret("ACRCLOUD_ACCESS_SECRET") or ""
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
    output = (
        MusicLightingOutputAdapter(lighting_controller)
        if lighting_controller is not None
        else None
    )
    music_lighting = MusicLightingController(
        output_callback=output.submit if output is not None else None,
        enabled_callback=output.set_enabled if output is not None else None,
    )
    return MusicVisualizerRuntime(
        analysis_source=source,
        song_recognition=SongRecognitionController(
            source,
            recognizer,
            metadata_cache,
            metadata_enricher=(lambda result: _enrich_from_spotify(result, spotify_controller)) if spotify_controller is not None else None,
        ),
        music_lighting=music_lighting,
        lighting_output=output,
    )


def _enrich_from_spotify(result, spotify_controller: SpotifyControllerIf):
    if not result.spotify_track_id:
        return result
    metadata = spotify_controller.track_metadata(result.spotify_track_id)
    if metadata is None:
        return result
    return replace(
        result,
        artwork_url=metadata.artwork_url,
        spotify_uri=metadata.uri,
        spotify_url=metadata.url or result.spotify_url,
    )
