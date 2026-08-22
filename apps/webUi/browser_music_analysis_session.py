# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Web transport adapter for the shared Python music-analysis subsystem."""
from __future__ import annotations

from dataclasses import asdict
import struct
import threading

from controllers.audio_analysis.music_analysis import MusicAnalysisState
from controllers.audio_analysis.pushed_pcm_music_analysis_source import PushedPcmMusicAnalysisSource


class WebBrowserMusicAnalysisSession:
    """Accept browser PCM while keeping all analysis in shared Python code."""

    def __init__(self, source: PushedPcmMusicAnalysisSource | None = None) -> None:
        self.source = source or PushedPcmMusicAnalysisSource()
        self._lock = threading.RLock()
        self._latest: MusicAnalysisState | None = None
        self.source.start(self._on_state)

    def _on_state(self, state: MusicAnalysisState) -> None:
        with self._lock:
            self._latest = state

    def push_pcm16(self, audio: bytes, sample_rate_hz: int) -> dict[str, object]:
        if not audio:
            raise ValueError("Empty PCM frame")
        if len(audio) % 2:
            raise ValueError("PCM16 frame must contain complete 16-bit samples")
        count = len(audio) // 2
        ints = struct.unpack(f"<{count}h", audio)
        samples = tuple(value / 32768.0 for value in ints)
        return self._state_dict(self.source.push_frame(samples, sample_rate_hz))

    def zeroize(self) -> dict[str, object]:
        self.source.zeroize()
        return self.state()

    def set_sensitivity(self, value: float) -> dict[str, object]:
        self.source.set_sensitivity(value)
        return self.state()

    def state(self) -> dict[str, object]:
        with self._lock:
            state = self._latest
        if state is None:
            return {
                "audio": {"level": 0.0, "bass": 0.0, "mid": 0.0, "treble": 0.0, "spectral_flux": 0.0, "spectrum": []},
                "percussion": {"kick": 0.0, "snare": 0.0, "tom_low": 0.0, "tom_mid": 0.0, "tom_high": 0.0, "cymbal": 0.0},
                "calibrated": self.source.calibrated,
                "sensitivity": self.source.sensitivity,
            }
        return self._state_dict(state)

    @staticmethod
    def _state_dict(state: MusicAnalysisState) -> dict[str, object]:
        data = asdict(state)
        data["audio"]["spectrum"] = list(state.audio.spectrum)
        return data
