from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SDRTelemetry:
    frequency_hz: Optional[int] = None
    signal: str = "--"
    snr: str = "--"
    rds: str = "--"


class SDRTelemetryMonitor:
    """
    Best-effort SDR++/rigctl telemetry reader.

    This class owns the rigctl query details so UI code does not have to.
    """

    def __init__(self, radio_controller) -> None:
        self.radio_controller = radio_controller

    def read(self, include_rds: bool = False) -> SDRTelemetry:
        frequency_hz = self._safe_get_frequency()
        signal = self._safe_client_call("get_signal_strength")
        snr = self._safe_client_call("get_snr")
        rds = self._safe_client_call("get_rds") if include_rds else "--"

        return SDRTelemetry(
            frequency_hz=frequency_hz,
            signal=signal,
            snr=snr,
            rds=rds,
        )

    def _safe_get_frequency(self) -> Optional[int]:
        try:
            backend = getattr(self.radio_controller, "backend", None)
            if backend is not None and hasattr(backend, "get_frequency"):
                return int(backend.get_frequency())

            value = getattr(self.radio_controller, "current_frequency_hz", None)
            return int(value) if value is not None else None
        except Exception:
            return getattr(self.radio_controller, "current_frequency_hz", None)

    def _safe_client_call(self, method_name: str) -> str:
        try:
            backend = getattr(self.radio_controller, "backend", None)
            client = getattr(backend, "client", None)

            if client is None:
                return "--"

            method = getattr(client, method_name, None)
            if method is None:
                return "--"

            value = method()
            return self._clean_rigctl_value(value)

        except Exception:
            return "--"

    def _clean_rigctl_value(self, value: object) -> str:
        text = str(value).strip() if value is not None else ""

        if not text:
            return "--"

        # SDR++ / rigctl returns this when the level command is unsupported.
        # Displaying it as telemetry is how machines mock us.
        if text.startswith("RPRT"):
            return "--"

        if "error" in text.lower():
            return "--"

        return text
