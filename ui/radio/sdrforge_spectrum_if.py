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
        if self.power_db is not None and (
            len(self.power_db) != len(self.bins)
            or any(not math.isfinite(value) for value in self.power_db)
        ):
            raise ValueError("power_db must match bins and contain finite values")
        if self.center_frequency_hz is not None and self.center_frequency_hz <= 0:
            raise ValueError("center frequency must be positive")
        if self.sample_rate_hz is not None and self.sample_rate_hz <= 0:
            raise ValueError("sample rate must be positive")


class SpectrumSourceIf(Protocol):
    """Application-owned source; polling must not block the UI thread."""

    def start(self) -> None:
        """Start spectrum acquisition."""
        ...

    def latest_spectrum(self) -> SpectrumPresentation | None:
        """Read the latest spectrum without blocking.
        @return Latest spectrum snapshot, or None if unavailable.
        """
        ...

    def latest_receiver(self) -> RadioTelemetry | None:
        """Read the latest receiver telemetry without blocking.
        @return Latest receiver telemetry, or None if unavailable.
        """
        ...

    def close(self) -> None:
        """Release spectrum acquisition resources."""
        ...


@runtime_checkable
class SpectrumPresentationIf(Protocol):
    """Frontend receives only validated, immutable spectrum snapshots."""

    def set_spectrum_presentation(self, snapshot: SpectrumPresentation) -> None:
        """Present an immutable spectrum snapshot.
        @param snapshot Validated spectrum display values.
        """
        ...


@dataclass(frozen=True, slots=True)
class SpectrumViewport:
    """Frequency window independent of receiver tuning and transport."""

    center_hz: float
    span_hz: float
    recenter_on_tune: bool = True

    def frequency_at(self, position: float) -> float:
        """Map normalized horizontal position to displayed frequency.
        @param position Normalized horizontal position (0 to 1 across the viewport).
        @return Displayed frequency in Hz.
        """
        return self.center_hz + (position - 0.5) * self.span_hz

    def pan(self, fraction: float) -> "SpectrumViewport":
        """Shift the viewport by a fraction of its visible bandwidth.
        @param fraction Signed fraction of the current span to shift.
        @return New viewport with the shifted center frequency.
        """
        from dataclasses import replace

        return replace(self, center_hz=self.center_hz + fraction * self.span_hz)

    def zoom(
        self, factor: float, *, min_span_hz: float = 100_000, max_span_hz: float | None = None
    ) -> "SpectrumViewport":
        """Zoom without changing the receiver's tuned frequency.
        @param factor Positive finite multiplier of the current span.
        @param min_span_hz Minimum requested span in Hz.
        @param max_span_hz Optional maximum span in Hz.
        @return New viewport with the adjusted span.
        """
        from dataclasses import replace

        if not math.isfinite(factor) or factor <= 0:
            raise ValueError("zoom factor must be finite and positive")
        span = max(min_span_hz, self.span_hz * factor)
        if max_span_hz is not None:
            span = min(span, max_span_hz)
        return replace(self, span_hz=span)


class SpectrumViewportControlIf(Protocol):
    """Frontend-neutral viewport operations; none retune the receiver."""

    def pan_spectrum(self, fraction: float) -> None:
        """Shift the displayed spectrum window.
        @param fraction Signed fraction of the visible span to shift.
        """
        ...

    def zoom_spectrum(self, factor: float) -> None:
        """Scale the displayed spectrum window.
        @param factor Positive multiplier of the visible span.
        """
        ...

    def set_recenter_on_tune(self, enabled: bool) -> None:
        """Set the viewport recentering policy.
        @param enabled Whether tuning should recenter the viewport.
        """
        ...
