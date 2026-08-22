# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import time

import numpy as np

from hardware_io.audio.audio_capture_if import AudioFrame


class SpectrumAnalysisMode(Enum):
    """How raw FFT energy is scaled for the visual spectrum."""

    NATIVE = "native"
    NORMALIZED = "normalized"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class AudioAnalysisState:
    """Normalized measurements derived from one PCM audio frame."""

    level: float
    peak: float
    bass: float
    mid: float
    treble: float
    spectrum: tuple[float, ...] = ()


class _AdaptiveNormalizer:
    def __init__(self, decay: float = 0.995, floor: float = 1e-9) -> None:
        self._peak = floor
        self._decay = decay
        self._floor = floor

    def normalize(self, value: float) -> float:
        self._peak = max(value, self._peak * self._decay, self._floor)
        return max(0.0, min(1.0, value / self._peak))

    def reset(self) -> None:
        self._peak = self._floor


class AudioAnalyzer:
    """Analyze PCM and provide zeroized, selectable spectrum scaling."""

    def __init__(self, spectrum_band_count: int = 24) -> None:
        self._bass_normalizer = _AdaptiveNormalizer()
        self._mid_normalizer = _AdaptiveNormalizer()
        self._treble_normalizer = _AdaptiveNormalizer()
        self._spectrum_normalizers = tuple(_AdaptiveNormalizer() for _ in range(spectrum_band_count))
        self._spectrum_global_normalizer = _AdaptiveNormalizer(decay=0.997)
        self._spectrum_band_count = spectrum_band_count
        self._spectrum_mode = SpectrumAnalysisMode.HYBRID
        self._has_calibration = False
        self._rms_floor = 0.0
        self._bass_floor = 0.0
        self._mid_floor = 0.0
        self._treble_floor = 0.0
        self._spectrum_floor = tuple(0.0 for _ in range(spectrum_band_count))
        self._zero_samples: list[tuple[float, float, float, float, tuple[float, ...]]] | None = None
        self._zero_deadline = 0.0

    @property
    def calibrated(self) -> bool:
        return self._zero_samples is None and self._has_calibration

    @property
    def spectrum_mode(self) -> SpectrumAnalysisMode:
        return self._spectrum_mode

    def set_spectrum_mode(self, mode: SpectrumAnalysisMode | str) -> None:
        self._spectrum_mode = mode if isinstance(mode, SpectrumAnalysisMode) else SpectrumAnalysisMode(str(mode))

    def begin_zeroize(self, duration_seconds: float = 1.5) -> None:
        self._zero_samples = []
        self._zero_deadline = time.monotonic() + max(0.5, float(duration_seconds))

    def analyze(self, frame: AudioFrame) -> AudioAnalysisState:
        samples = np.asarray(frame.samples, dtype=np.float64)
        if samples.size == 0:
            return AudioAnalysisState(0.0, 0.0, 0.0, 0.0, 0.0)

        peak = float(np.max(np.abs(samples)))
        rms = float(np.sqrt(np.mean(samples * samples)))
        windowed = samples * np.hanning(samples.size)
        fft = np.abs(np.fft.rfft(windowed))
        frequencies = np.fft.rfftfreq(samples.size, d=1.0 / frame.sample_rate_hz)

        def band_energy(low_hz: float, high_hz: float) -> float:
            mask = (frequencies >= low_hz) & (frequencies < high_hz)
            return float(math.sqrt(np.mean(fft[mask] ** 2))) if np.any(mask) else 0.0

        bass_raw = band_energy(20.0, 250.0)
        mid_raw = band_energy(250.0, 4000.0)
        treble_raw = band_energy(4000.0, 16000.0)
        edges = np.geomspace(31.25, 16000.0, self._spectrum_band_count + 1)
        spectrum_raw = tuple(band_energy(float(low), float(high)) for low, high in zip(edges[:-1], edges[1:]))

        if self._zero_samples is not None:
            self._zero_samples.append((rms, bass_raw, mid_raw, treble_raw, spectrum_raw))
            if time.monotonic() >= self._zero_deadline:
                self._finish_zeroize()
            return AudioAnalysisState(0.0, max(0.0, min(1.0, peak)), 0.0, 0.0, 0.0, tuple(0.0 for _ in range(self._spectrum_band_count)))

        rms_excess = max(0.0, rms - self._rms_floor * 1.15)
        bass_excess = max(0.0, bass_raw - self._bass_floor * 1.18)
        mid_excess = max(0.0, mid_raw - self._mid_floor * 1.18)
        treble_excess = max(0.0, treble_raw - self._treble_floor * 1.18)
        excess = tuple(max(0.0, raw - floor * 1.18) for raw, floor in zip(spectrum_raw, self._spectrum_floor))

        normalized = tuple(n.normalize(value) for value, n in zip(excess, self._spectrum_normalizers))
        global_peak = max(excess, default=0.0)
        global_scale = self._spectrum_global_normalizer.normalize(global_peak)
        native_denom = max(global_peak, 1e-9)
        native = tuple(max(0.0, min(1.0, (value / native_denom) * global_scale)) for value in excess)

        if self._spectrum_mode is SpectrumAnalysisMode.NATIVE:
            spectrum_values = native
        elif self._spectrum_mode is SpectrumAnalysisMode.NORMALIZED:
            spectrum_values = normalized
        else:
            spectrum_values = tuple(n * 0.55 + a * 0.45 for n, a in zip(native, normalized))

        return AudioAnalysisState(
            level=max(0.0, min(1.0, rms_excess * 4.0)),
            peak=max(0.0, min(1.0, peak)),
            bass=self._bass_normalizer.normalize(bass_excess),
            mid=self._mid_normalizer.normalize(mid_excess),
            treble=self._treble_normalizer.normalize(treble_excess),
            spectrum=spectrum_values,
        )

    def _finish_zeroize(self) -> None:
        samples = self._zero_samples or []
        if not samples:
            self._zero_samples = None
            return
        index = min(len(samples) - 1, int(len(samples) * 0.80))

        def percentile(values: list[float]) -> float:
            ordered = sorted(values)
            return ordered[index] if ordered else 0.0

        self._rms_floor = percentile([sample[0] for sample in samples])
        self._bass_floor = percentile([sample[1] for sample in samples])
        self._mid_floor = percentile([sample[2] for sample in samples])
        self._treble_floor = percentile([sample[3] for sample in samples])
        self._spectrum_floor = tuple(percentile([sample[4][band] for sample in samples]) for band in range(self._spectrum_band_count))
        self._has_calibration = True
        self._zero_samples = None
        self._bass_normalizer.reset()
        self._mid_normalizer.reset()
        self._treble_normalizer.reset()
        self._spectrum_global_normalizer.reset()
        for normalizer in self._spectrum_normalizers:
            normalizer.reset()
