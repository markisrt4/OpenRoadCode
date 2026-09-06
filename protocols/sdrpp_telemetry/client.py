"""Client for the OpenRoadCode SDR++ read-only telemetry protocol."""

from __future__ import annotations

from dataclasses import dataclass
import socket


@dataclass(frozen=True)
class SDRPPTelemetry:
    snr_db: float | None = None
    signal_peak_db: float | None = None
    fft_average_db: float | None = None
    center_frequency_hz: float | None = None
    bandwidth_hz: float | None = None
    view_bandwidth_hz: float | None = None
    fft_min_db: float | None = None
    fft_max_db: float | None = None
    waterfall_min_db: float | None = None
    waterfall_max_db: float | None = None
    selected_vfo: str | None = None


class SDRPPTelemetryClient:
    """Small request/response client for the ORC SDR++ telemetry module."""

    def __init__(self, host: str = "127.0.0.1", port: int = 4534, timeout_s: float = 0.5) -> None:
        self.host = host
        self.port = port
        self.timeout_s = timeout_s

    def ping(self) -> bool:
        return self._request("PING") == "OK"

    def read(self) -> SDRPPTelemetry:
        response = self._request("GET telemetry")
        if not response.startswith("TELEMETRY "):
            raise RuntimeError(f"Unexpected SDR++ telemetry response: {response!r}")

        values: dict[str, str] = {}
        for field in response.removeprefix("TELEMETRY ").split():
            key, separator, value = field.partition("=")
            if separator:
                values[key] = value

        return SDRPPTelemetry(
            snr_db=self._float(values.get("snr")),
            signal_peak_db=self._float(values.get("signal_peak")),
            fft_average_db=self._float(values.get("fft_average")),
            center_frequency_hz=self._float(values.get("center_frequency")),
            bandwidth_hz=self._float(values.get("bandwidth")),
            view_bandwidth_hz=self._float(values.get("view_bandwidth")),
            fft_min_db=self._float(values.get("fft_min")),
            fft_max_db=self._float(values.get("fft_max")),
            waterfall_min_db=self._float(values.get("waterfall_min")),
            waterfall_max_db=self._float(values.get("waterfall_max")),
            selected_vfo=values.get("selected_vfo"),
        )

    def _request(self, command: str) -> str:
        with socket.create_connection((self.host, self.port), timeout=self.timeout_s) as connection:
            connection.settimeout(self.timeout_s)
            connection.sendall((command + "\n").encode("utf-8"))
            chunks: list[bytes] = []
            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                if b"\n" in chunk:
                    break
        response = b"".join(chunks).decode("utf-8", errors="replace").strip()
        if response.startswith("ERROR "):
            raise RuntimeError(response)
        return response

    @staticmethod
    def _float(value: str | None) -> float | None:
        if value is None or value.lower() == "nan":
            return None
        try:
            return float(value)
        except ValueError:
            return None
