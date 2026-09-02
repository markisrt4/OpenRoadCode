# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for OpenRoadCode's SDR++ application remote-control module."""

from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class SDRPPTelemetry:
    snr_db: float
    center_frequency_hz: float
    bandwidth_hz: float
    view_bandwidth_hz: float
    fft_min_db: float
    fft_max_db: float
    waterfall_min_db: float
    waterfall_max_db: float
    selected_vfo: str | None


class SDRPPRemoteControlClient:
    """Send application-control and telemetry commands to SDR++."""

    def __init__(self, host: str = "127.0.0.1", port: int = 4533, timeout: float = 0.75) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, command: str) -> str:
        if not command or not command.strip():
            raise ValueError("SDR++ remote-control command must not be empty")
        wire_command = command.rstrip() + "\n"
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            sock.sendall(wire_command.encode("utf-8"))
            response = sock.recv(4096).decode("utf-8", errors="replace").strip()
        if not response:
            raise RuntimeError("SDR++ remote control returned no response")
        return response

    def ping(self) -> bool:
        try:
            return self.send("PING") == "OK"
        except (OSError, RuntimeError):
            return False

    def _get_value(self, name: str) -> str:
        response = self.send(f"GET {name}")
        prefix = f"VALUE {name} "
        if not response.startswith(prefix):
            raise RuntimeError(f"Unexpected SDR++ {name} response: {response!r}")
        return response[len(prefix):].strip()

    def _get_float(self, name: str) -> float:
        value = self._get_value(name)
        try:
            return float(value)
        except ValueError as exc:
            raise RuntimeError(f"Invalid SDR++ {name} value: {value!r}") from exc

    def _get_toggle(self, name: str) -> bool:
        value = self._get_value(name).lower()
        if value == "on": return True
        if value == "off": return False
        raise RuntimeError(f"Unexpected SDR++ {name} value: {value!r}")

    def _set_toggle(self, name: str, enabled: bool) -> bool:
        value = "on" if enabled else "off"
        response = self.send(f"SET {name} {value}")
        if response == "OK": return enabled
        if response.startswith("ERROR "):
            raise RuntimeError(f"SDR++ rejected {name} setting: {response}")
        raise RuntimeError(f"Unexpected SDR++ set-{name} response: {response!r}")

    def _toggle(self, name: str) -> bool:
        response = self.send(f"TOGGLE {name}")
        prefix = f"VALUE {name} "
        if not response.startswith(prefix):
            raise RuntimeError(f"Unexpected SDR++ {name} toggle response: {response!r}")
        value = response[len(prefix):].strip().lower()
        if value == "on": return True
        if value == "off": return False
        raise RuntimeError(f"Unexpected SDR++ {name} value: {value!r}")

    def get_theme(self) -> str: return self._get_value("theme")

    def get_themes(self) -> tuple[str, ...]:
        response = self.send("GET themes")
        prefix = "VALUES themes "
        if not response.startswith(prefix):
            raise RuntimeError(f"Unexpected SDR++ themes response: {response!r}")
        return tuple(name for name in response[len(prefix):].split("|") if name)

    def set_theme(self, theme: str) -> bool:
        selected = theme.strip()
        if not selected:
            raise ValueError("SDR++ theme must not be empty")
        response = self.send(f"SET theme {selected}")
        if response == "OK": return True
        if response.startswith("ERROR "): return False
        raise RuntimeError(f"Unexpected SDR++ set-theme response: {response!r}")

    def get_waterfall(self) -> bool: return self._get_toggle("waterfall")
    def set_waterfall(self, visible: bool) -> bool: return self._set_toggle("waterfall", visible)
    def toggle_waterfall(self) -> bool: return self._toggle("waterfall")
    def get_bandplan(self) -> bool: return self._get_toggle("bandplan")
    def set_bandplan(self, visible: bool) -> bool: return self._set_toggle("bandplan", visible)
    def toggle_bandplan(self) -> bool: return self._toggle("bandplan")
    def get_fft_hold(self) -> bool: return self._get_toggle("fft_hold")
    def set_fft_hold(self, enabled: bool) -> bool: return self._set_toggle("fft_hold", enabled)
    def toggle_fft_hold(self) -> bool: return self._toggle("fft_hold")

    def get_snr(self) -> float: return self._get_float("snr")
    def get_center_frequency(self) -> float: return self._get_float("center_frequency")
    def get_bandwidth(self) -> float: return self._get_float("bandwidth")
    def get_view_bandwidth(self) -> float: return self._get_float("view_bandwidth")
    def get_fft_min(self) -> float: return self._get_float("fft_min")
    def get_fft_max(self) -> float: return self._get_float("fft_max")
    def get_waterfall_min(self) -> float: return self._get_float("waterfall_min")
    def get_waterfall_max(self) -> float: return self._get_float("waterfall_max")
    def get_selected_vfo(self) -> str | None:
        value = self._get_value("selected_vfo")
        return None if value == "none" else value

    def get_telemetry(self) -> SDRPPTelemetry:
        response = self.send("GET telemetry")
        prefix = "TELEMETRY "
        if not response.startswith(prefix):
            raise RuntimeError(f"Unexpected SDR++ telemetry response: {response!r}")
        fields = {}
        for item in response[len(prefix):].split():
            key, separator, value = item.partition("=")
            if separator:
                fields[key] = value
        required = {
            "snr", "center_frequency", "bandwidth", "view_bandwidth",
            "fft_min", "fft_max", "waterfall_min", "waterfall_max", "selected_vfo",
        }
        missing = required.difference(fields)
        if missing:
            raise RuntimeError(f"SDR++ telemetry missing fields: {', '.join(sorted(missing))}")
        return SDRPPTelemetry(
            snr_db=float(fields["snr"]),
            center_frequency_hz=float(fields["center_frequency"]),
            bandwidth_hz=float(fields["bandwidth"]),
            view_bandwidth_hz=float(fields["view_bandwidth"]),
            fft_min_db=float(fields["fft_min"]),
            fft_max_db=float(fields["fft_max"]),
            waterfall_min_db=float(fields["waterfall_min"]),
            waterfall_max_db=float(fields["waterfall_max"]),
            selected_vfo=None if fields["selected_vfo"] == "none" else fields["selected_vfo"],
        )

    def auto_range(self) -> bool:
        response = self.send("ACTION auto_range")
        if response == "OK": return True
        if response.startswith("ERROR "): return False
        raise RuntimeError(f"Unexpected SDR++ auto-range response: {response!r}")
