# SPDX-License-Identifier: MIT
"""Frontend-neutral contracts for native SDR spectrum presentation."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol, runtime_checkable
from ui.radio.rf_radio_if import RadioTelemetry


@dataclass(frozen=True, slots=True)
class SpectrumPresentation:
    """Normalized immutable display bins, independent of transport and Tk."""

    bins: tuple[float, ...]
    center_frequency_hz: int | None = None
    sample_rate_hz: int | None = None
    power_db: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if not self.bins or any(not 0.0 <= value <= 1.0 for value in self.bins):
            raise ValueError("spectrum bins must be nonempty and normalized")
        if self.power_db is not None and (len(self.power_db) != len(self.bins)
                or any(not math.isfinite(value) for value in self.power_db)):
            raise ValueError("power_db must match bins and contain finite values")
        if self.center_frequency_hz is not None and self.center_frequency_hz <= 0:
            raise ValueError("center frequency must be positive")
        if self.sample_rate_hz is not None and self.sample_rate_hz <= 0:
            raise ValueError("sample rate must be positive")


class SpectrumSourceIf(Protocol):
    """Application-owned source; polling must not block the UI thread."""

    def start(self) -> None: ...

    def latest_spectrum(self) -> SpectrumPresentation | None: ...

    def latest_receiver(self) -> RadioTelemetry | None: ...

    def close(self) -> None: ...


@runtime_checkable
class SpectrumPresentationIf(Protocol):
    """Frontend receives only validated, immutable spectrum snapshots."""

    def set_spectrum_presentation(self, snapshot: SpectrumPresentation) -> None: ...
