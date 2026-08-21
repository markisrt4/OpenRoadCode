# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared FFT-based music analysis implementation.

The analyzer intentionally owns signal processing only. Audio capture and UI
rendering belong to adapters/frontends so carUi and webUi can consume the same
analysis state.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .music_analysis_types import MusicAnalysisState, PercussionActivity
from .music_analyzer_if import MusicAnalyzerIf


class MusicAnalyzer(MusicAnalyzerIf):
    """Analyze normalized mono PCM using a Hann-windowed real FFT."""

    _ZEROIZE_PERCENTILE = 75.0
    _ZEROIZE_MARGIN_DB = 3.0

    def __init__(self, *, fft_size: int = 2048, band_count: int = 24) -> None:
        if fft_size < 256 or fft_size & (fft_size - 1):
            raise ValueError("fft_size must be a power of two >= 256")
        if band_count < 3:
            raise ValueError("band_count must be >= 3")
        self.fft_size = fft_size
        self.band_count = band_count
        self._window = np.hanning(fft_size).astype(np.float32)
        self._band_peaks = np.full(band_count, 1e-6, dtype=np.float32)
        self._summary_peaks = {"bass": 1e-6, "mid": 1e-6, "treble": 1e-6}
        self._activity_peaks = {name: 1e-6 for name in ("kick", "bass", "snare", "tom_high", "tom_mid", "tom_low", "cymbal")}
        self._previous_activity = {name: 0.0 for name in self._activity_peaks}
        self._zeroize_collecting = False
        self._zeroize_frames: list[np.ndarray] = []
        self._noise_floor: np.ndarray | None = None

    @property
    def is_zeroized(self) -> bool:
        return self._noise_floor is not None

    def start_zeroize(self) -> None:
        self._zeroize_frames.clear()
        self._zeroize_collecting = True

    def finish_zeroize(self) -> None:
        if not self._zeroize_frames:
            self._zeroize_collecting = False
            raise RuntimeError("zeroize requires at least one analyzed audio block")
        frames = np.stack(self._zeroize_frames)
        self._noise_floor = np.percentile(frames, self._ZEROIZE_PERCENTILE, axis=0).astype(np.float32)
        self._zeroize_frames.clear()
        self._zeroize_collecting = False
        self._reset_adaptive_state()

    def clear_zeroize(self) -> None:
        self._zeroize_frames.clear()
        self._zeroize_collecting = False
        self._noise_floor = None
        self._reset_adaptive_state()

    def analyze(self, samples: Sequence[float], sample_rate_hz: int) -> MusicAnalysisState:
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        pcm = np.asarray(samples, dtype=np.float32).reshape(-1)
        if pcm.size < self.fft_size:
            pcm = np.pad(pcm, (self.fft_size - pcm.size, 0))
        elif pcm.size > self.fft_size:
            pcm = pcm[-self.fft_size :]
        pcm = np.clip(pcm, -1.0, 1.0)
        pcm = pcm - float(np.mean(pcm))
        magnitude = np.abs(np.fft.rfft(pcm * self._window)) / max(float(np.sum(self._window)) / 2.0, 1e-9)
        frequencies = np.fft.rfftfreq(self.fft_size, d=1.0 / sample_rate_hz)
        if self._zeroize_collecting:
            self._zeroize_frames.append(magnitude.copy())
        gated_magnitude = self._gate_ambient(magnitude)
        level = min(1.0, float(np.sqrt(np.mean(pcm * pcm))) * 4.0)
        bass = self._normalized_band(gated_magnitude, frequencies, 20, 250, "bass")
        mid = self._normalized_band(gated_magnitude, frequencies, 250, 4000, "mid")
        treble = self._normalized_band(gated_magnitude, frequencies, 4000, 16000, "treble")
        return MusicAnalysisState(level=level,bass=bass,mid=mid,treble=treble,spectrum=self._spectrum(gated_magnitude, frequencies, sample_rate_hz),percussion=self._percussion(gated_magnitude, frequencies),sample_rate_hz=sample_rate_hz,fft_size=self.fft_size)

    def _gate_ambient(self, magnitude: np.ndarray) -> np.ndarray:
        if self._noise_floor is None or self._noise_floor.shape != magnitude.shape:
            return magnitude
        threshold = self._noise_floor * (10.0 ** (self._ZEROIZE_MARGIN_DB / 20.0))
        return np.maximum(magnitude - threshold, 0.0)

    def _reset_adaptive_state(self) -> None:
        self._band_peaks.fill(1e-6)
        for key in self._summary_peaks:self._summary_peaks[key]=1e-6
        for key in self._activity_peaks:self._activity_peaks[key]=1e-6;self._previous_activity[key]=0.0

    @staticmethod
    def _band_rms(magnitude: np.ndarray, frequencies: np.ndarray, low_hz: float, high_hz: float) -> float:
        values=magnitude[(frequencies>=low_hz)&(frequencies<high_hz)]
        return float(np.sqrt(np.mean(values*values))) if values.size else 0.0

    def _normalized_band(self,magnitude,frequencies,low_hz,high_hz,key):
        raw=self._band_rms(magnitude,frequencies,low_hz,high_hz);peak=max(raw,self._summary_peaks[key]*.992,1e-6);self._summary_peaks[key]=peak;return min(1.0,raw/peak)

    def _spectrum(self,magnitude,frequencies,sample_rate_hz):
        edges=np.geomspace(31.25,min(16000.0,sample_rate_hz/2.0),self.band_count+1);output=[]
        for index,(low,high) in enumerate(zip(edges[:-1],edges[1:])):
            raw=self._band_rms(magnitude,frequencies,float(low),float(high));peak=max(raw,float(self._band_peaks[index])*.992,1e-6);self._band_peaks[index]=peak;output.append(min(1.0,raw/peak))
        return tuple(output)

    def _activity(self,name,raw,transient_weight):
        if raw<=1e-8:self._previous_activity[name]=0.0;return 0.0
        peak=max(raw,self._activity_peaks[name]*.994,1e-6);self._activity_peaks[name]=peak;normalized=min(1.0,raw/peak);rise=max(0.0,normalized-self._previous_activity[name]);self._previous_activity[name]=normalized;return min(1.0,normalized*(1.0-transient_weight)+rise*2.6*transient_weight)

    def _percussion(self,magnitude,frequencies):
        band=lambda low,high:self._band_rms(magnitude,frequencies,low,high)
        kick_raw=band(45,105);bass_raw=band(55,260);snare_body=band(160,300);snare_crack=band(1500,5200);cymbal_raw=band(6000,15000)
        # Overlap is deliberate: acoustic tom fundamentals and harmonics do not
        # respect neat frequency cubicles. Transient scoring does the rest.
        tom_high_raw=band(145,260);tom_mid_raw=band(105,195);tom_low_raw=band(70,135)
        cymbal=self._activity("cymbal",cymbal_raw,.56);snare=self._activity("snare",max(0.0,snare_body*.44+snare_crack*.76-cymbal_raw*.22),.92);bass=self._activity("bass",bass_raw,.16);kick=self._activity("kick",kick_raw,.80)
        tom_high=max(0.0,self._activity("tom_high",tom_high_raw,.88)-bass*.14-kick*.08)
        tom_mid=max(0.0,self._activity("tom_mid",tom_mid_raw,.89)-bass*.18-kick*.11)
        tom_low=max(0.0,self._activity("tom_low",tom_low_raw,.90)-bass*.22-kick*.14)
        return PercussionActivity(kick=kick,bass=bass,snare=snare,tom_high=tom_high,tom_mid=tom_mid,tom_low=tom_low,cymbal=cymbal)
