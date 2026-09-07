# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Source-independent music analysis and calibration ownership."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
import struct
import threading

from controllers.audio.capture.audio_capture_if import AudioCaptureIf
from .music_analysis_types import MusicAnalysisState
from .music_analyzer import MusicAnalyzer


class PushAudioCapture(AudioCaptureIf):
    """Adapt external PCM transport to the standard capture contract."""

    def __init__(self) -> None:
        self._callback = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, callback) -> None:
        if self._running:
            raise RuntimeError("audio capture is already running")
        self._callback = callback
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._callback = None

    def push(self, samples: Sequence[float], sample_rate_hz: int) -> None:
        callback = self._callback
        if not self._running or callback is None:
            raise RuntimeError("audio source is not running")
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        callback(samples, sample_rate_hz)

    def push_pcm16(self, audio: bytes, sample_rate_hz: int) -> None:
        if not audio or len(audio) % 2:
            raise ValueError("PCM16 frame must contain complete 16-bit samples")
        count = len(audio) // 2
        self.push(tuple(value / 32768.0 for value in struct.unpack(f"<{count}h", audio)), sample_rate_hz)


class MusicAnalysisSession:
    """Own one analyzer, one selected capture, and one calibration profile.

    Factories are supplied by platform composition. Source changes clear the
    noise profile and adaptive state. Lifecycle operations are serialized and
    callbacks from previous capture generations are ignored. Consumers receive
    raw MusicAnalysisState, never presentation-gained values.
    """

    def __init__(self, sources: Mapping[str, Callable[[], AudioCaptureIf]], *,
                 analyzer: MusicAnalyzer | None = None, consumer=None) -> None:
        if not sources:
            raise ValueError("at least one audio source is required")
        self._sources = dict(sources)
        self._analyzer = analyzer or MusicAnalyzer()
        self._consumer = consumer
        self._lock = threading.RLock()
        self._lifecycle = threading.RLock()
        self._source: str | None = None
        self._capture: AudioCaptureIf | None = None
        self._latest: MusicAnalysisState | None = None
        self._generation = 0
        self._calibrating = False

    def sources(self) -> tuple[str, ...]:
        """Return registered source identifiers in presentation order."""
        return tuple(self._sources)

    def select(self, source: str) -> dict[str, object]:
        """Select a source without starting it, stopping the previous one."""
        with self._lifecycle:
            if source not in self._sources:
                raise ValueError(f"Unknown audio source: {source}")
            if source == self._source:
                return self.state()
            self.stop()
            with self._lock:
                self._analyzer.clear_zeroize()
                self._calibrating = False
                self._latest = None
                self._capture = None
                self._source = None
            capture = self._sources[source]()
            with self._lock:
                self._capture = capture
                self._source = source
            return self.state()

    def start(self, source: str | None = None) -> dict[str, object]:
        """Start the selected source, or select and start a named source."""
        with self._lifecycle:
            if source is not None:
                self.select(source)
            with self._lock:
                capture = self._capture
                if capture is None:
                    raise ValueError("Select an audio source first")
                if capture.is_running:
                    return self.state()
                self._generation += 1
                generation = self._generation
            try:
                capture.start(lambda samples, rate: self._on_samples(generation, samples, rate))
            except Exception:
                with self._lock:
                    self._generation += 1
                try:
                    capture.stop()
                except Exception:
                    pass  # Preserve the original backend-start failure.
                raise
            return self.state()

    def stop(self) -> dict[str, object]:
        """Stop capture, invalidating callbacks before releasing resources."""
        with self._lifecycle:
            with self._lock:
                self._generation += 1
                capture = self._capture
                if self._calibrating:
                    # An unfinished collection must never continue after restart.
                    # Clearing also discards the previous noise profile, explicitly.
                    self._analyzer.clear_zeroize()
                    self._calibrating = False
            if capture is not None:
                capture.stop()
            return self.state()

    def push_pcm16(self, audio: bytes, sample_rate_hz: int, *, source: str = "browser") -> dict[str, object]:
        """Decode a little-endian PCM16 frame from the selected push source."""
        capture = self._push_source(source)
        capture.push_pcm16(audio, sample_rate_hz)
        return self.state()

    def push(self, samples: Sequence[float], sample_rate_hz: int, *, source: str) -> dict[str, object]:
        """Accept normalized PCM from an external capture transport."""
        capture = self._push_source(source)
        capture.push(samples, sample_rate_hz)
        return self.state()

    def _push_source(self, source: str) -> PushAudioCapture:
        with self._lock:
            if self._source != source or not isinstance(self._capture, PushAudioCapture):
                raise RuntimeError("Selected audio source does not accept external PCM")
            if not self._capture.is_running:
                raise RuntimeError("audio source is not running")
            return self._capture

    def state(self) -> dict[str, object]:
        """Return raw analyzer state and source/calibration lifecycle status."""
        with self._lock:
            if self._latest is None:
                data: dict[str, object] = {
                    "level": 0.0, "bass": 0.0, "mid": 0.0, "treble": 0.0,
                    "spectrum": [0.0] * self._analyzer.band_count,
                    "percussion": {key: 0.0 for key in (
                        "kick", "bass", "snare", "tom_high", "tom_mid", "tom_low", "cymbal")},
                    "sample_rate_hz": 0, "fft_size": self._analyzer.fft_size,
                }
            else:
                data = asdict(self._latest)
                data["spectrum"] = list(self._latest.spectrum)
            data.update(source=self._source, running=bool(self._capture and self._capture.is_running),
                        zeroized=self._analyzer.is_zeroized, calibrating=self._calibrating)
            return data

    def start_zeroize(self) -> dict[str, object]:
        """Collect ambient-noise frames from the currently running source."""
        with self._lock:
            if self._capture is None or not self._capture.is_running:
                raise RuntimeError("Start an audio source before calibration")
            self._analyzer.start_zeroize()
            self._calibrating = True
            return self.state()

    def finish_zeroize(self) -> dict[str, object]:
        """Commit the collected noise profile, or report an empty collection."""
        with self._lock:
            try:
                self._analyzer.finish_zeroize()
            finally:
                self._calibrating = False
            return self.state()

    def clear_zeroize(self) -> dict[str, object]:
        """Discard calibration and reset the analyzer's adaptive state."""
        with self._lock:
            self._analyzer.clear_zeroize()
            self._calibrating = False
            return self.state()

    def _on_samples(self, generation: int, samples: Sequence[float], sample_rate_hz: int) -> None:
        with self._lock:
            if generation != self._generation:
                return
            state = self._analyzer.analyze(samples, sample_rate_hz)
            self._latest = state
        if self._consumer is not None:
            self._consumer(state)
