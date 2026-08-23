# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Runtime-selectable PCM input for music analysis."""
from __future__ import annotations

from collections.abc import Callable
from enum import Enum
import threading

from hardware_io.audio.audio_capture_if import AudioCaptureIf

from .audio_analysis import SpectrumAnalysisMode
from .music_analysis import MusicAnalysisState
from .pcm_music_analysis_source import PcmMusicAnalysisSource


class MusicAudioInput(Enum):
    """Audio streams that can drive music analysis."""

    SYSTEM_AUDIO = "system_audio"
    EXTERNAL_INPUT = "external_input"


class SelectableMusicAnalysisSource:
    """Switch capture devices without replacing analysis consumers."""

    def __init__(self, captures: dict[MusicAudioInput, Callable[[], AudioCaptureIf]], initial_input: MusicAudioInput = MusicAudioInput.SYSTEM_AUDIO) -> None:
        if initial_input not in captures:
            raise ValueError(f"capture is not configured for {initial_input.value}")
        self._captures = dict(captures)
        self._input = initial_input
        self._source = self._create_source(initial_input)
        self._callback: Callable[[MusicAnalysisState], None] | None = None
        self._running = False
        self._lock = threading.RLock()

    @property
    def input(self) -> MusicAudioInput:return self._input
    @property
    def sensitivity(self) -> float:return self._source.sensitivity
    @property
    def calibrated(self) -> bool:return self._source.calibrated
    @property
    def spectrum_mode(self) -> SpectrumAnalysisMode:return self._source.spectrum_mode
    @property
    def buffered_audio_seconds(self) -> float:return self._source.buffered_audio_seconds

    def start(self, callback: Callable[[MusicAnalysisState], None]) -> None:
        with self._lock:self._callback=callback;self._source.start(callback);self._running=True

    def stop(self) -> None:
        with self._lock:self._running=False;self._source.stop()

    def select_input(self, selected: MusicAudioInput | str) -> None:
        selected=selected if isinstance(selected,MusicAudioInput) else MusicAudioInput(selected)
        with self._lock:
            if selected is self._input:return
            old=self._source;sensitivity=old.sensitivity;spectrum_mode=old.spectrum_mode;running=self._running;callback=self._callback
            if running:old.stop()
            replacement=self._create_source(selected);replacement.set_sensitivity(sensitivity);replacement.set_spectrum_mode(spectrum_mode)
            self._source=replacement;self._input=selected
            if running and callback is not None:replacement.start(callback)

    def zeroize(self) -> None:self._source.zeroize()
    def set_sensitivity(self, value: float) -> None:self._source.set_sensitivity(value)
    def set_spectrum_mode(self, mode: SpectrumAnalysisMode | str) -> None:self._source.set_spectrum_mode(mode)
    def recent_audio_pcm16(self, seconds: float = 6.0) -> bytes:return self._source.recent_audio_pcm16(seconds)
    def recent_audio_wav(self, seconds: float = 6.0) -> bytes:return self._source.recent_audio_wav(seconds)

    def _create_source(self, selected: MusicAudioInput) -> PcmMusicAnalysisSource:
        try:capture=self._captures[selected]()
        except KeyError as exc:raise ValueError(f"capture is not configured for {selected.value}") from exc
        return PcmMusicAnalysisSource(capture=capture)
