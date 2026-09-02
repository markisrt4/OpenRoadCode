# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Client for OpenRoadCode's SDR++ application remote-control module."""

from __future__ import annotations

import socket


class SDRPPRemoteControlClient:
    """Send application-control commands to a running SDR++ instance."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4533,
        timeout: float = 0.75,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, command: str) -> str:
        """Send one command and return the stripped single-line response."""
        if not command or not command.strip():
            raise ValueError("SDR++ remote-control command must not be empty")

        wire_command = command.rstrip() + "\n"
        with socket.create_connection(
            (self.host, self.port), timeout=self.timeout
        ) as sock:
            sock.settimeout(self.timeout)
            sock.sendall(wire_command.encode("utf-8"))
            response = sock.recv(4096).decode("utf-8", errors="replace").strip()

        if not response:
            raise RuntimeError("SDR++ remote control returned no response")
        return response

    def ping(self) -> bool:
        """Return True when the SDR++ remote-control module is responsive."""
        try:
            return self.send("PING") == "OK"
        except (OSError, RuntimeError):
            return False

    def get_theme(self) -> str:
        """Return SDR++'s current theme name."""
        response = self.send("GET theme")
        prefix = "VALUE theme "
        if not response.startswith(prefix):
            raise RuntimeError(f"Unexpected SDR++ theme response: {response!r}")
        return response[len(prefix):]

    def get_themes(self) -> tuple[str, ...]:
        """Return theme names exposed by the running SDR++ instance."""
        response = self.send("GET themes")
        prefix = "VALUES themes "
        if not response.startswith(prefix):
            raise RuntimeError(f"Unexpected SDR++ themes response: {response!r}")
        value = response[len(prefix):]
        return tuple(name for name in value.split("|") if name)

    def set_theme(self, theme: str) -> bool:
        """Apply a theme immediately to the running SDR++ instance."""
        selected = theme.strip()
        if not selected:
            raise ValueError("SDR++ theme must not be empty")
        response = self.send(f"SET theme {selected}")
        if response == "OK":
            return True
        if response.startswith("ERROR "):
            return False
        raise RuntimeError(f"Unexpected SDR++ set-theme response: {response!r}")
