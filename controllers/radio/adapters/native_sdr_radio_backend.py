# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native SDR tuner backend for the existing radio controller contract.

This first increment controls one physical tuner. IQ channelization, audio,
telemetry and RDS are separate upcoming components, not simulated here.
"""

from __future__ import annotations

from hardware_io.sdr.sdr_source_if import SdrSourceIf
from controllers.radio.radio_backend_if import RadioBackendIf


class NativeSdrRadioBackend(RadioBackendIf):
    """Control an injected SDR source without exposing device details to UI."""

    _MODES = {"WFM", "NFM", "AM"}

    def __init__(self, source: SdrSourceIf, *, initial_frequency_hz: int = 104_300_000,
                 sample_rate_hz: int = 2_400_000, gain_db: float | None = 30.0) -> None:
        if initial_frequency_hz <= 0 or sample_rate_hz <= 0:
            raise ValueError("frequency and sample rate must be positive")
        self._source = source
        self._frequency_hz = initial_frequency_hz
        self._sample_rate_hz = sample_rate_hz
        self._gain_db = gain_db
        self._mode = "WFM"
        self._bandwidth_hz = 200_000
        self._started = False

    def start(self) -> str:
        if self._started:
            return "started"
        self._source.open()
        try:
            self._source.set_sample_rate(self._sample_rate_hz)
            self._source.set_gain(self._gain_db)
            self._source.set_center_frequency(self._frequency_hz)
            self._source.start()
        except Exception:
            self._source.close()
            raise
        self._started = True
        return "started"

    def stop(self) -> str:
        if self._started:
            try:
                self._source.stop()
            finally:
                self._started = False
                self._source.close()
        return "stopped"

    def set_frequency(self, frequency_hz: int) -> str:
        if frequency_hz <= 0:
            raise ValueError("frequency must be positive")
        if self._started:
            self._source.set_center_frequency(frequency_hz)
        self._frequency_hz = frequency_hz
        return str(frequency_hz)

    def get_frequency(self) -> int:
        return self._source.get_center_frequency() if self._started else self._frequency_hz

    def set_mode(self, mode: str, bandwidth: int) -> str:
        normalized = mode.upper()
        if normalized not in self._MODES:
            raise ValueError(f"unsupported native SDR mode: {mode}")
        if bandwidth <= 0:
            raise ValueError("bandwidth must be positive")
        self._mode = normalized
        self._bandwidth_hz = bandwidth
        return normalized

    def get_signal_strength(self) -> None:
        return None  # No RF measurement pipeline attached yet.

    def get_snr(self) -> None:
        return None  # Never invent a signal-to-noise ratio.

    def get_rds(self) -> None:
        return None  # RDS decoder will attach to the WFM multiplex path.
