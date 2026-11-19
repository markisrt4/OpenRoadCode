# SPDX-License-Identifier: MIT
"""Validate and normalize libSDRForge ZMQ spectrum snapshots for the RF UI."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class SdrForgeSpectrumFrame:
    """One FFT row with absolute RF frequency coordinates."""

    timestamp_ns: int
    center_frequency_hz: int
    sample_rate_hz: int
    first_bin_frequency_hz: float
    bin_spacing_hz: float
    power_db: tuple[float | None, ...]

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> SdrForgeSpectrumFrame:
        """Parse the existing SDRForge spectrum topic without DSP dependencies."""
        timestamp = payload["timestamp_ns"]
        center = payload["center_frequency_hz"]
        rate = payload["sample_rate_hz"]
        count = payload["bin_count"]
        first = payload["first_bin_frequency_hz"]
        spacing = payload["bin_spacing_hz"]
        values = payload["power_db"]
        if not all(type(value) is int for value in (timestamp, center, rate, count)):
            raise TypeError("spectrum timestamp, frequency, rate and count must be integers")
        if timestamp < 0 or center <= 0 or rate <= 0 or count <= 0:
            raise ValueError("invalid spectrum metadata")
        if not isinstance(values, (list, tuple)) or len(values) != count:
            raise ValueError("spectrum bin count mismatch")
        if type(first) not in (int, float) or type(spacing) not in (int, float):
            raise TypeError("spectrum frequency coordinates must be numeric")
        if not isfinite(first) or not isfinite(spacing) or spacing <= 0:
            raise ValueError("invalid spectrum frequency coordinates")
        expected_first = center - rate / 2
        expected_spacing = rate / count
        if abs(first - expected_first) > 1e-6 or abs(spacing - expected_spacing) > 1e-6:
            raise ValueError("inconsistent spectrum frequency coordinates")
        bins: list[float | None] = []
        for value in values:
            if value is None:
                bins.append(None)
            elif type(value) in (int, float) and isfinite(value):
                bins.append(float(value))
            else:
                raise ValueError("invalid spectrum power bin")
        return cls(timestamp, center, rate, float(first), float(spacing), tuple(bins))

    def frequency_hz(self, index: int) -> float:
        """Return the absolute RF frequency at a bin index."""
        if not 0 <= index < len(self.power_db):
            raise IndexError(index)
        return self.first_bin_frequency_hz + index * self.bin_spacing_hz
