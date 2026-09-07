# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own one analyzer and select interchangeable PCM capture backends."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
import struct
import threading

from controllers.audio.capture.audio_capture_if import AudioCaptureIf
from .music_analysis_pipeline import MusicAnalysisPipeline
from .music_analysis_types import MusicAnalysisState
from .music_analyzer import MusicAnalyzer


class PushAudioCapture(AudioCaptureIf):
    """Adapt PCM supplied by an external transport to AudioCaptureIf.

    The transport owns permissions and acquisition. This adapter owns only
    the callback and accepts frames while the source is selected and running.
    """

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
        if not self._running or self._callback is None:
            raise RuntimeError("audio source is not running")
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        self._callback(samples, sample_rate_hz)

    def push_pcm16(self, audio: bytes, sample_rate_hz: int) -> None:
        if not audio or len(audio) % 2:
            raise ValueError("PCM16 frame must contain complete 16-bit samples")
        count = len(audio) // 2
        self.push(tuple(value / 32768.0 for value in struct.unpack(f"<{count}h", audio)), sample_rate_hz)


class MusicAnalysisSession:
    """Select one source, analyze PCM, and publish shared analysis state.

    Source factories are injected by composition. No platform-specific capture
    implementation is imported here. Switching stops the old source before
    starting the next. Calibration is cleared on source changes because noise
    profiles belong to the acquisition path, not to the visualizer.
    """

    def __init__(self, sources: Mapping[str, Callable[[], AudioCaptureIf]], *,
                 analyzer: MusicAnalyzer | None = None, consumer=None) -> None:
        if not sources:
            raise ValueError("at least one audio source is required")
        self._sources = dict(sources)
        self._analyzer = analyzer or MusicAnalyzer()
        self._consumer = consumer
        self._lock = threading.RLock()
        self._source: str | None = None
        self._capture: AudioCaptureIf | None = None
        self._pipeline: MusicAnalysisPipeline | None = None
        self._latest: MusicAnalysisState | None = None
        self._generation = 0
        self._calibrating = False

    def sources(self) -> tuple[str, ...]:
        return tuple(self._sources)

    def select(self, source: str) -> dict[str, object]:
        with self._lock:
            if source not in self._sources:
                raise ValueError(f"Unknown audio source: {source}")
            if source == self._source:
                return self.state()
            self._stop_locked()
            self._analyzer.clear_zeroize()
            self._calibrating = False
            self._latest = None
            self._capture = self._sources[source]()
            self._source = source
            self._pipeline = MusicAnalysisPipeline(self._capture, self._analyzer, self._on_state)
            return self.state()

    def start(self, source: str | None = None) -> dict[str, object]:
        with self._lock:
            if source is not None:
                self.select(source)
            if self._pipeline is None:
                raise ValueError("Select an audio source first")
            if not self._pipeline.is_running:
                self._pipeline.start()
            return self.state()

    def stop(self) -> dict[str, object]:
        with self._lock:
            self._stop_locked()
            return self.state()

    def _stop_locked(self) -> None:
        self._generation += 1
        if self._pipeline is not None and self._pipeline.is_running:
            self._pipeline.stop()
        self._calibrating = False

    def push_pcm16(self, audio: bytes, sample_rate_hz: int, *, source: str = "browser") -> dict[str, object]:
        with self._lock:
            if self._source != source or not isinstance(self._capture, PushAudioCapture):
                raise RuntimeError("Selected audio source does not accept browser PCM")
            self._capture.push_pcm16(audio, sample_rate_hz)
            return self.state()

    def push(self, samples: Sequence[float], sample_rate_hz: int, *, source: str) -> dict[str, object]:
        with self._lock:
            if self._source != source or not isinstance(self._capture, PushAudioCapture):
                raise RuntimeError("Selected audio source does not accept external PCM")
            self._capture.push(samples, sample_rate_hz)
            return self.state()

    def state(self) -> dict[str, object]:
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
            data.update(source=self._source, running=bool(self._pipeline and self._pipeline.is_running),
                        zeroized=self._analyzer.is_zeroized, calibrating=self._calibrating)
            return data

    def start_zeroize(self) -> dict[str, object]:
        with self._lock:
            if self._pipeline is None or not self._pipeline.is_running:
                raise RuntimeError("Start an audio source before calibration")
            self._analyzer.start_zeroize()
            self._calibrating = True
            return self.state()

    def finish_zeroize(self) -> dict[str, object]:
        with self._lock:
            self._analyzer.finish_zeroize()
            self._calibrating = False
            return self.state()

    def clear_zeroize(self) -> dict[str, object]:
        with self._lock:
            self._analyzer.clear_zeroize()
            self._calibrating = False
            return self.state()

    def _on_state(self, state: MusicAnalysisState) -> None:
        with self._lock:
            self._latest = state
        if self._consumer is not None:
            self._consumer(state)
