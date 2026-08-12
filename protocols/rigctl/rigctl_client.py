# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Small TCP client for Hamlib-style rigctl servers and SDR++ extensions."""

from __future__ import annotations

import socket

SDRPP_MODE_MAP = {
    "NFM": "FM",
    "FM": "FM",
    "WFM": "WFM",
    "AM": "AM",
}


class RigctlClient:
    """Send one rigctl command per TCP connection.

    This connection pattern works well with SDR++'s rigctl server and keeps the
    client deliberately stateless. An empty string is returned when a command
    produces no response before the configured timeout.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4532,
        timeout: float = 1.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, command: str) -> str:
        """Send a raw command and return the stripped server response."""
        if not command or not command.strip():
            raise ValueError("rigctl command must not be empty")

        wire_command = command.rstrip() + "\n"

        with socket.create_connection(
            (self.host, self.port), timeout=self.timeout
        ) as sock:
            sock.settimeout(self.timeout)
            sock.sendall(wire_command.encode("utf-8"))

            try:
                return sock.recv(4096).decode(
                    "utf-8", errors="replace"
                ).strip()
            except socket.timeout:
                return ""

    def set_frequency(self, hz: int) -> str:
        """Set receiver frequency in hertz."""
        if hz <= 0:
            raise ValueError("frequency must be greater than zero")
        return self.send(f"F {hz}")

    def get_frequency(self) -> str:
        """Return the receiver frequency in hertz as reported by the server."""
        return self.send("f")

    def set_mode(self, mode: str, bandwidth: int) -> str:
        """Set demodulation mode and bandwidth in hertz."""
        if not mode or not mode.strip():
            raise ValueError("mode must not be empty")
        if bandwidth < 0:
            raise ValueError("bandwidth must not be negative")

        rigctl_mode = self.normalize_sdrpp_mode(mode)
        return self.send(f"M {rigctl_mode} {bandwidth}")

    def start(self) -> str:
        """Start SDR++ playback using its rigctl extension."""
        return self.send(r"\start")

    def stop(self) -> str:
        """Stop SDR++ playback using its rigctl extension."""
        return self.send(r"\stop")

    def get_signal_strength(self) -> str:
        """Return the current signal-strength level."""
        return self.send("l STRENGTH")

    def get_snr(self) -> str:
        """Return the current signal-to-noise ratio."""
        return self.send("l SNR")

    def get_rds(self) -> str:
        """Return the current RDS text when supported by the server."""
        return self.send("l RDS")

    @staticmethod
    def normalize_sdrpp_mode(mode: str) -> str:
        """Translate application-facing mode names to SDR++ rigctl names."""
        normalized = mode.strip().upper()
        return SDRPP_MODE_MAP.get(normalized, normalized)
