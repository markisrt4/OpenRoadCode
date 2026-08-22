# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Web transport adapter for the shared Python music-analysis subsystem."""
from __future__ import annotations

from dataclasses import asdict
import struct
import threading

from controllers.audio_analysis.music_analysis import MusicAnalysisState
from controllers.audio_analysis.music_analysis_presenter import MusicAnalysisPresenter
from controllers.audio_analysis.pushed_pcm_music_analysis_source import PushedPcmMusicAnalysisSource
from ui.music_analysis import MusicAnalysisUiIf, MusicAnalysisUiState


class WebBrowserMusicAnalysisSession(MusicAnalysisUiIf):
    """Accept browser PCM and expose the same semantic analysis UI state as carUi."""

    def __init__(self, source: PushedPcmMusicAnalysisSource | None = None) -> None:
        self.source = source or PushedPcmMusicAnalysisSource()
        self._lock = threading.RLock()
        self._latest: MusicAnalysisState | None = None
        self._ui_state: MusicAnalysisUiState | None = None
        self.presenter = MusicAnalysisPresenter(self.source)
        self.presenter.attach_ui(self)
        self.presenter.start()

    def set_analysis_state(self, state: MusicAnalysisState) -> None:
        with self._lock:
            self._latest = state

    def set_analysis_ui_state(self, state: MusicAnalysisUiState) -> None:
        with self._lock:
            self._ui_state = state

    def push_pcm16(self, audio: bytes, sample_rate_hz: int) -> dict[str, object]:
        if not audio:
            raise ValueError("Empty PCM frame")
        if len(audio) % 2:
            raise ValueError("PCM16 frame must contain complete 16-bit samples")
        count = len(audio) // 2
        ints = struct.unpack(f"<{count}h", audio)
        samples = tuple(value / 32768.0 for value in ints)
        self.source.push_frame(samples, sample_rate_hz)
        return self.state()

    def zeroize(self) -> dict[str, object]:
        self.presenter.request_zeroize()
        return self.state()

    def set_sensitivity(self, value: float) -> dict[str, object]:
        self.presenter.request_sensitivity(value)
        return self.state()

    def state(self) -> dict[str, object]:
        with self._lock:
            state = self._latest
            ui_state = self._ui_state
        if state is None:
            data: dict[str, object] = {
                "audio": {"level": 0.0, "peak": 0.0, "bass": 0.0, "mid": 0.0, "treble": 0.0, "spectral_flux": 0.0, "spectrum": []},
                "percussion": {"kick": 0.0, "snare": 0.0, "tom_low": 0.0, "tom_mid": 0.0, "tom_high": 0.0, "cymbal": 0.0},
                "calibrated": self.source.calibrated,
                "sensitivity": self.source.sensitivity,
            }
        else:
            data = self._state_dict(state)
        if ui_state is not None:
            data["ui"] = {
                "status": ui_state.status.value,
                "calibrated": ui_state.calibrated,
                "sensitivity": ui_state.sensitivity,
                "error": ui_state.error,
            }
        return data

    @staticmethod
    def _state_dict(state: MusicAnalysisState) -> dict[str, object]:
        data = asdict(state)
        data["audio"]["spectrum"] = list(state.audio.spectrum)
        return data
