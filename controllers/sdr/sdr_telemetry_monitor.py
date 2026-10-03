# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from common.logging.structured import event
from protocols.sdrpp_telemetry import SDRPPTelemetry, SDRPPTelemetryClient

LOGGER = logging.getLogger("radio.sdr.telemetry")


@dataclass(frozen=True)
class SDRTelemetry:
    """Best-effort receiver telemetry suitable for frontend presentation."""

    frequency_hz: Optional[int] = None
    signal: str = "--"
    snr: str = "--"
    rds: str = "--"


class SDRTelemetryMonitor:
    """Combine SDR++ runtime telemetry with radio-specific RDS data.

    Signal measurements come from the dedicated read-only SDR++ telemetry
    protocol on port 4534. RDS remains a radio concern and is obtained through
    the radio controller only when explicitly requested.

    ``read`` performs socket I/O. Graphical frontends must call it from a
    worker/background thread rather than their UI thread.
    """

    def __init__(
        self,
        radio_controller,
        telemetry_client: SDRPPTelemetryClient | None = None,
    ) -> None:
        self._telemetry_available: bool | None = None
        self._rds_available: bool | None = None
        self.radio_controller = radio_controller
        self.telemetry_client = telemetry_client or SDRPPTelemetryClient()

    def read(self, include_rds: bool = False) -> SDRTelemetry:
        """Read one best-effort snapshot without propagating backend failures."""
        snapshot = self._safe_read_telemetry()
        frequency_hz = self._frequency(snapshot)
        signal = self._format_db(snapshot.signal_peak_db if snapshot else None)
        snr = self._format_db(snapshot.snr_db if snapshot else None)
        rds = self._safe_read_rds() if include_rds else "--"
        return SDRTelemetry(frequency_hz=frequency_hz, signal=signal, snr=snr, rds=rds)

    def _safe_read_telemetry(self) -> SDRPPTelemetry | None:
        try:
            snapshot = self.telemetry_client.read()
        except Exception as error:
            if self._telemetry_available is not False:
                event(
                    LOGGER,
                    logging.WARNING,
                    "telemetry.unavailable",
                    "SDR telemetry unavailable",
                    exception_type=type(error).__name__,
                )
            self._telemetry_available = False
            return None
        if self._telemetry_available is False:
            event(LOGGER, logging.INFO, "telemetry.recovered", "SDR telemetry recovered")
        self._telemetry_available = True
        event(LOGGER, logging.DEBUG, "telemetry.received", "SDR telemetry snapshot received")
        return snapshot

    def _frequency(self, snapshot: SDRPPTelemetry | None) -> Optional[int]:
        if snapshot is not None and snapshot.center_frequency_hz is not None:
            return int(round(snapshot.center_frequency_hz))
        try:
            value = getattr(self.radio_controller, "current_frequency_hz", None)
            if value is None:
                state = getattr(self.radio_controller, "state", None)
                value = getattr(state, "frequency_hz", None)
            return int(value) if value is not None else None
        except (OSError, RuntimeError, TypeError, ValueError):
            return None

    def _safe_read_rds(self) -> str:
        try:
            method = getattr(self.radio_controller, "read_rds", None)
            if method is None:
                method = getattr(self.radio_controller, "get_rds", None)
            if method is None:
                return "--"
            text = self._clean_text(method())
        except Exception as error:
            if self._rds_available is not False:
                event(
                    LOGGER,
                    logging.WARNING,
                    "rds.unavailable",
                    "Radio RDS read unavailable",
                    exception_type=type(error).__name__,
                )
            self._rds_available = False
            return "--"
        if self._rds_available is False:
            event(LOGGER, logging.INFO, "rds.recovered", "Radio RDS read recovered")
        self._rds_available = True
        return text

    @staticmethod
    def _format_db(value: float | None) -> str:
        return "--" if value is None else f"{value:.1f} dB"

    @staticmethod
    def _clean_text(value: object) -> str:
        text = str(value).strip() if value is not None else ""
        if not text or text.startswith("RPRT") or "error" in text.lower():
            return "--"
        return text
