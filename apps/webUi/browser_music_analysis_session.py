# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""HTTP transport adapter for browser PCM music analysis."""
from __future__ import annotations

from dataclasses import asdict
import struct
import threading

from controllers.audio.music_analysis import MusicAnalyzer


class WebBrowserMusicAnalysisSession:
    """Analyze PCM16 frames supplied by a browser microphone capture."""

    def __init__(self, analyzer: MusicAnalyzer | None = None) -> None:
        self._analyzer = analyzer or MusicAnalyzer()
        self._lock = threading.RLock()
        self._latest = None

    def push_pcm16(self, audio: bytes, sample_rate_hz: int) -> dict[str, object]:
        """Analyze one little-endian mono PCM16 frame and return browser state."""
        if not audio:
            raise ValueError("Empty PCM frame")
        if len(audio) % 2:
            raise ValueError("PCM16 frame must contain complete 16-bit samples")
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")

        count = len(audio) // 2
        integers = struct.unpack(f"<{count}h", audio)
        samples = tuple(value / 32768.0 for value in integers)
        with self._lock:
            self._latest = self._analyzer.analyze(samples, sample_rate_hz)
            return self._state_dict(self._latest)

    def state(self) -> dict[str, object]:
        """Return the latest analysis state, or an idle state before first audio."""
        with self._lock:
            if self._latest is None:
                return {
                    "level": 0.0,
                    "bass": 0.0,
                    "mid": 0.0,
                    "treble": 0.0,
                    "spectrum": [0.0] * self._analyzer.band_count,
                    "percussion": {
                        "kick": 0.0,
                        "bass": 0.0,
                        "snare": 0.0,
                        "tom_high": 0.0,
                        "tom_mid": 0.0,
                        "tom_low": 0.0,
                        "cymbal": 0.0,
                    },
                    "sample_rate_hz": 0,
                    "fft_size": self._analyzer.fft_size,
                    "zeroized": self._analyzer.is_zeroized,
                }
            return self._state_dict(self._latest)

    def start_zeroize(self) -> dict[str, object]:
        """Begin collecting frames for ambient-noise calibration."""
        with self._lock:
            self._analyzer.start_zeroize()
            return self.state()

    def finish_zeroize(self) -> dict[str, object]:
        """Finish ambient-noise calibration."""
        with self._lock:
            self._analyzer.finish_zeroize()
            return self.state()

    def clear_zeroize(self) -> dict[str, object]:
        """Clear the ambient-noise calibration."""
        with self._lock:
            self._analyzer.clear_zeroize()
            return self.state()

    def _state_dict(self, state) -> dict[str, object]:
        data = asdict(state)
        data["spectrum"] = list(state.spectrum)
        data["zeroized"] = self._analyzer.is_zeroized
        return data
