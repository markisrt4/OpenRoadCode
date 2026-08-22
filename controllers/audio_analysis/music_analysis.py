# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Higher-level music analysis built on the generic PCM analyzer."""
from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import math
import time

import numpy as np

from hardware_io.audio.audio_capture_if import AudioFrame
from .audio_analysis import AudioAnalyzer, AudioAnalysisState


@dataclass(frozen=True)
class PercussionState:
    kick: float = 0.0
    snare: float = 0.0
    tom_low: float = 0.0
    tom_mid: float = 0.0
    tom_high: float = 0.0
    cymbal: float = 0.0


@dataclass(frozen=True)
class MusicAnalysisState:
    audio: AudioAnalysisState
    percussion: PercussionState
    calibrated: bool
    sensitivity: float


class MusicAnalyzer:
    """Analyze PCM for visualizer-oriented spectrum and percussion activity."""

    _BANDS = {
        "kick": (42.0, 105.0),
        "tom_low": (70.0, 135.0),
        "tom_mid": (105.0, 195.0),
        "tom_high": (145.0, 280.0),
        "snare_body": (180.0, 420.0),
        "snare_crack": (1500.0, 5200.0),
        "cymbal": (6000.0, 15000.0),
    }

    def __init__(self, spectrum_band_count: int = 24) -> None:
        self._base = AudioAnalyzer(spectrum_band_count=spectrum_band_count)
        self._sensitivity = 1.0
        self._noise_floor: dict[str, float] = {}
        self._zero_samples: list[dict[str, float]] | None = None
        self._zero_deadline = 0.0
        self._peaks = {name: 1e-9 for name in self._BANDS}
        self._previous = {name: 0.0 for name in self._BANDS}
        self._last_hit = {name: -1e9 for name in ("kick", "snare", "tom_low", "tom_mid", "tom_high", "cymbal")}
        self._recent = deque(maxlen=3)

    @property
    def sensitivity(self) -> float:
        return self._sensitivity

    @property
    def calibrated(self) -> bool:
        return self._zero_samples is None and bool(self._noise_floor) and self._base.calibrated

    def set_sensitivity(self, value: float) -> None:
        self._sensitivity = max(0.25, min(2.0, float(value)))

    def begin_zeroize(self, duration_seconds: float = 1.5) -> None:
        duration = max(0.5, float(duration_seconds))
        self._zero_samples = []
        self._zero_deadline = time.monotonic() + duration
        self._base.begin_zeroize(duration)

    def analyze(self, frame: AudioFrame) -> MusicAnalysisState:
        audio = self._base.analyze(frame)
        energies = self._band_energies(frame)
        if self._zero_samples is not None:
            self._zero_samples.append(energies)
            if time.monotonic() >= self._zero_deadline:
                self._finish_zeroize()
            return MusicAnalysisState(audio, PercussionState(), self.calibrated, self._sensitivity)

        normalized: dict[str, float] = {}
        rises: dict[str, float] = {}
        for name, raw in energies.items():
            floor = self._noise_floor.get(name, 0.0)
            excess = max(0.0, raw - floor * 1.18)
            self._peaks[name] = max(excess, self._peaks[name] * 0.994, 1e-9)
            value = min(1.0, excess / self._peaks[name]) * self._sensitivity
            value = min(1.0, value)
            normalized[name] = value
            rises[name] = max(0.0, value - self._previous[name])
            self._previous[name] = value
        self._recent.append((normalized, rises))
        return MusicAnalysisState(audio, self._classify(normalized, rises), self.calibrated, self._sensitivity)

    def _finish_zeroize(self) -> None:
        samples = self._zero_samples or []
        floor: dict[str, float] = {}
        for name in self._BANDS:
            values = sorted(sample[name] for sample in samples)
            floor[name] = values[min(len(values) - 1, int(len(values) * 0.80))] if values else 0.0
        self._noise_floor = floor
        self._zero_samples = None
        self._peaks = {name: 1e-9 for name in self._BANDS}
        self._previous = {name: 0.0 for name in self._BANDS}

    def _band_energies(self, frame: AudioFrame) -> dict[str, float]:
        samples = np.asarray(frame.samples, dtype=np.float64)
        if samples.size == 0:
            return {name: 0.0 for name in self._BANDS}
        windowed = samples * np.hanning(samples.size)
        spectrum = np.abs(np.fft.rfft(windowed))
        freq = np.fft.rfftfreq(samples.size, d=1.0 / frame.sample_rate_hz)
        result: dict[str, float] = {}
        for name, (low, high) in self._BANDS.items():
            mask = (freq >= low) & (freq < high)
            result[name] = float(math.sqrt(np.mean(spectrum[mask] ** 2))) if np.any(mask) else 0.0
        return result

    def _classify(self, n: dict[str, float], rise: dict[str, float]) -> PercussionState:
        now = time.monotonic()
        candidates = {
            "kick": n["kick"] * .70 + rise["kick"] * .95 - n["tom_mid"] * .18,
            "tom_low": n["tom_low"] * .68 + rise["tom_low"] * .85 - n["kick"] * .24,
            "tom_mid": n["tom_mid"] * .72 + rise["tom_mid"] * .90 - n["kick"] * .18,
            "tom_high": n["tom_high"] * .72 + rise["tom_high"] * .90 - n["kick"] * .12,
            "snare": n["snare_body"] * .40 + n["snare_crack"] * .65 + rise["snare_crack"] * .85,
            "cymbal": n["cymbal"] * .62 + rise["cymbal"] * 1.05,
        }
        thresholds = {"kick": .20, "tom_low": .22, "tom_mid": .20, "tom_high": .22, "snare": .24, "cymbal": .24}
        cooldown = {"kick": .085, "tom_low": .115, "tom_mid": .105, "tom_high": .110, "snare": .155, "cymbal": .130}
        active = {name: 0.0 for name in candidates}
        ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
        for name, score in ranked[:2]:
            if score < thresholds[name] or now - self._last_hit[name] < cooldown[name]:
                continue
            active[name] = min(1.0, score)
            self._last_hit[name] = now
        return PercussionState(
            kick=active["kick"], snare=active["snare"], tom_low=active["tom_low"],
            tom_mid=active["tom_mid"], tom_high=active["tom_high"], cymbal=active["cymbal"],
        )