# SPDX-License-Identifier: MIT
"""Frontend-neutral contracts for native SDR spectrum presentation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from ui.radio.rf_radio_if import RadioTelemetry


@dataclass(frozen=True, slots=True)
class SpectrumPresentation:
    """Normalized immutable display bins, independent of transport and Tk."""

    bins: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.bins or any(not 0.0 <= value <= 1.0 for value in self.bins):
            raise ValueError("spectrum bins must be nonempty and normalized")


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
