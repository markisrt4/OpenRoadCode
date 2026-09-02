# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for OpenRoadCode's SDR++ application remote-control module."""

from __future__ import annotations

import socket


class SDRPPRemoteControlClient:
    """Send application-control commands to a running SDR++ instance."""

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

    def _get_toggle(self, name: str) -> bool:
        response = self.send(f"GET {name}")
        prefix = f"VALUE {name} "
        if not response.startswith(prefix):
            raise RuntimeError(f"Unexpected SDR++ {name} response: {response!r}")
        value = response[len(prefix):].strip().lower()
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

    def get_theme(self) -> str:
        response = self.send("GET theme")
        prefix = "VALUE theme "
        if not response.startswith(prefix):
            raise RuntimeError(f"Unexpected SDR++ theme response: {response!r}")
        return response[len(prefix):]

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

    def auto_range(self) -> bool:
        response = self.send("ACTION auto_range")
        if response == "OK": return True
        if response.startswith("ERROR "): return False
        raise RuntimeError(f"Unexpected SDR++ auto-range response: {response!r}")
