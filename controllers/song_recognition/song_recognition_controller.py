# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Orchestrate asynchronous song recognition independent of any frontend."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import io
import logging
import math
import threading
import wave
from pathlib import Path

import numpy as np

from controllers.audio_analysis.music_analysis_source_if import MusicAnalysisSourceIf
from .song_metadata_cache import SongMetadataCache
from .song_recognition_if import SongRecognitionIf, SongRecognitionResult

LOGGER=logging.getLogger(__name__)
MIN_RECOGNITION_SECONDS = 10.0


SongRecognitionCallback = Callable[[SongRecognitionResult | None], None]
SongRecognitionErrorCallback = Callable[[str], None]


class SongRecognitionController:
    """Recognize recent analyzed audio and persist normalized metadata."""

    def __init__(
        self,
        source: MusicAnalysisSourceIf,
        recognizer: SongRecognitionIf,
        metadata_cache: SongMetadataCache,
        metadata_enricher: Callable[[SongRecognitionResult], SongRecognitionResult] | None = None,
    ) -> None:
        self._source = source
        self._recognizer = recognizer
        self._metadata_cache = metadata_cache
        self._metadata_enricher = metadata_enricher
        self._lock = threading.Lock()
        self._last_clip_summary: str | None = None

    @property
    def is_configured(self) -> bool:
        return self._recognizer.is_configured

    @property
    def provider_name(self) -> str | None:
        return self._recognizer.provider_name

    @property
    def last_clip_summary(self) -> str | None:
        return self._last_clip_summary

    @property
    def buffered_audio_seconds(self) -> float:
        return self._source.buffered_audio_seconds

    @property
    def is_ready(self) -> bool:
        return self.buffered_audio_seconds >= MIN_RECOGNITION_SECONDS

    def identify_async(
        self,
        on_result: SongRecognitionCallback,
        on_error: SongRecognitionErrorCallback,
        *,
        sample_seconds: float = 10.0,
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
            audio = self._source.recent_audio_wav(sample_seconds)
            if not audio:
                raise RuntimeError("No recent audio is available yet")
            self._last_clip_summary=self._describe_wav(audio)
            diagnostic_path=Path("/tmp/openroadcode-recognition-last.wav");diagnostic_path.write_bytes(audio);LOGGER.info("Recognition clip saved to %s (%s)",diagnostic_path,self._last_clip_summary)
            result = self._recognizer.recognize(audio, sample_bytes=len(audio))
            if result is not None:
                cached_result = self._metadata_cache.get_result(result)
                if cached_result is not None:
                    result = cached_result
                    LOGGER.info("Reused cached metadata for recognized song")
                elif self._metadata_enricher is not None:
                    try:
                        result = self._metadata_enricher(result)
                    except Exception:
                        LOGGER.exception("Song metadata enrichment failed; using recognition metadata")
                self._metadata_cache.put_result_ids(result)
                LOGGER.info("Song recognized by %s: %s · %s",self._recognizer.provider_name,result.title," · ".join(result.artists))
            else:
                LOGGER.warning("No song match from %s (%s)",self._recognizer.provider_name or "recognizer",self._last_clip_summary)
            on_result(result)
        except Exception as exc:
            LOGGER.exception("Song recognition request failed")
            on_error(str(exc))
        finally:
            self._lock.release()

    @staticmethod
    def _describe_wav(audio: bytes) -> str:
        try:
            with wave.open(io.BytesIO(audio),"rb") as clip:
                rate=clip.getframerate();frames=clip.getnframes();width=clip.getsampwidth();raw=clip.readframes(frames)
            if rate<=0 or width!=2:raise ValueError("expected 16-bit PCM WAV")
            samples=np.frombuffer(raw,dtype="<i2").astype(np.float64)/32768.0;duration=frames/rate;rms=float(np.sqrt(np.mean(samples*samples))) if samples.size else 0.0;dbfs=20*math.log10(max(rms,1e-9))
            if duration<MIN_RECOGNITION_SECONDS:
                raise RuntimeError(
                    f"Only {duration:.1f}s of audio is buffered; "
                    "let the song play for at least 10 seconds, then try again"
                )
            if rms<0.0005:raise RuntimeError(f"Recognition clip is effectively silent ({dbfs:.0f} dBFS)")
            return f"{duration:.1f}s clip · {dbfs:.0f} dBFS"
        except (wave.Error,ValueError) as exc:
            raise RuntimeError(f"Invalid recognition WAV: {exc}") from exc
