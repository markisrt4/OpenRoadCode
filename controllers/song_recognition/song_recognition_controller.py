# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Orchestrate asynchronous song recognition independent of any frontend."""
from __future__ import annotations

from collections.abc import Callable
import threading

from controllers.audio_analysis.music_analysis_source_if import MusicAnalysisSourceIf
from .song_metadata_cache import SongMetadataCache
from .song_recognition_if import SongRecognitionIf, SongRecognitionResult


SongRecognitionCallback = Callable[[SongRecognitionResult | None], None]
SongRecognitionErrorCallback = Callable[[str], None]


class SongRecognitionController:
    """Recognize recent analyzed audio and persist normalized metadata."""

    def __init__(
        self,
        source: MusicAnalysisSourceIf,
        recognizer: SongRecognitionIf,
        metadata_cache: SongMetadataCache,
    ) -> None:
        self._source = source
        self._recognizer = recognizer
        self._metadata_cache = metadata_cache
        self._lock = threading.Lock()

    @property
    def is_configured(self) -> bool:
        return self._recognizer.is_configured

    @property
    def provider_name(self) -> str | None:
        return self._recognizer.provider_name

    def identify_async(
        self,
        on_result: SongRecognitionCallback,
        on_error: SongRecognitionErrorCallback,
        *,
        sample_seconds: float = 6.0,
    ) -> bool:
        """Start one recognition request and return False if one is in flight."""
        if not self._recognizer.is_configured:
            on_result(None)
            return False
        if not self._lock.acquire(blocking=False):
            return False
        threading.Thread(
            target=self._identify,
            args=(sample_seconds, on_result, on_error),
            name="song-recognition",
            daemon=True,
        ).start()
        return True

    def _identify(
        self,
        sample_seconds: float,
        on_result: SongRecognitionCallback,
        on_error: SongRecognitionErrorCallback,
    ) -> None:
        try:
            audio = self._source.recent_audio_pcm16(sample_seconds)
            if not audio:
                raise RuntimeError("No recent audio is available yet")
            result = self._recognizer.recognize(audio, sample_bytes=len(audio))
            if result is not None:
                self._metadata_cache.put_result_ids(result)
            on_result(result)
        except Exception as exc:
            on_error(str(exc))
        finally:
            self._lock.release()
