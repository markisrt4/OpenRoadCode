# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic in-memory radio controller."""

from __future__ import annotations

from collections.abc import Sequence

from .radio_backend_if import RadioBackendIf
from .radio_controller import RadioController
from .radio_types import RadioMode, RadioPreset, RadioRange


class _StubRadioBackend(RadioBackendIf):
    def __init__(
        self,
        *,
        signal_strength: float | str | None,
        snr: float | str | None,
        rds: str | None,
    ) -> None:
        self.frequency_hz = 0
        self.mode = ""
        self.bandwidth = 0
        self.signal_strength = signal_strength
        self.snr = snr
        self.rds = rds
        self.running = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def get_frequency(self) -> int:
        return self.frequency_hz

    def set_frequency(self, frequency_hz: int) -> None:
        self.frequency_hz = frequency_hz

    def set_mode(self, mode: str, bandwidth: int) -> None:
        self.mode = mode
        self.bandwidth = bandwidth

    def get_signal_strength(self) -> float | str | None:
        return self.signal_strength

    def get_snr(self) -> float | str | None:
        return self.snr

    def get_rds(self) -> str | None:
        return self.rds


class RadioControllerStub(RadioController):
    """Provide deterministic tuning and telemetry without a receiver."""

    DEFAULT_MODE = RadioMode("WFM", bandwidth=180_000, step_hz=100_000)
    DEFAULT_RANGE = RadioRange(
        min_frequency_hz=87_500_000,
        max_frequency_hz=108_000_000,
        start_frequency_hz=88_100_000,
    )

    def __init__(
        self,
        *,
        presets: Sequence[RadioPreset] = (),
        default_mode: RadioMode = DEFAULT_MODE,
        radio_range: RadioRange | None = DEFAULT_RANGE,
        signal_strength: float | str | None = -42.0,
        snr: float | str | None = 30.0,
        rds: str | None = "OpenRoadCode",
    ) -> None:
        backend = _StubRadioBackend(
            signal_strength=signal_strength,
            snr=snr,
            rds=rds,
        )
        self._stub_backend = backend
        super().__init__(
            backend=backend,
            presets=list(presets),
            default_mode=default_mode,
            radio_range=radio_range,
        )
