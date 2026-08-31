# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import socket
import time

from hardware_io.automotive.elm327.elm327_errors import (
    Elm327CommandError,
    Elm327ConnectionError,
)
from hardware_io.automotive.elm327.elm327_response import Elm327Response


class Elm327TcpDevice:
    """TCP connection to an ELM327-compatible byte stream."""

    INITIALIZATION_COMMANDS = ("ATZ", "ATE0", "ATL0", "ATS0", "ATH1", "ATSP0")

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 35000,
        timeout: float = 1.0,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._socket: socket.socket | None = None

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> None:
        if self.is_connected:
            return
        try:
            self._socket = socket.create_connection(
                (self._host, self._port),
                timeout=self._timeout,
            )
            self._socket.settimeout(self._timeout)
            self._initialize()
        except (Elm327CommandError, Elm327ConnectionError) as exc:
            self.disconnect()
            raise Elm327ConnectionError(
                f"Connected to {self._host}:{self._port}, but ELM327 "
                f"initialization failed: {exc}"
            ) from exc
        except OSError as exc:
            self.disconnect()
            raise Elm327ConnectionError(
                f"Unable to connect to ELM327 TCP bridge at "
                f"{self._host}:{self._port}"
            ) from exc

    def disconnect(self) -> None:
        if self._socket is None:
            return
        try:
            self._socket.close()
        finally:
            self._socket = None

    def send_command(
        self,
        command: str,
        delay: float = 0.0,
    ) -> Elm327Response:
        if self._socket is None:
            raise Elm327ConnectionError("ELM327 device is not connected")

        normalized_command = command.strip().upper()
        if not normalized_command:
            raise ValueError("command cannot be empty")

        try:
            self._drain_input()
            self._socket.sendall(f"{normalized_command}\r".encode("ascii"))
            if delay > 0:
                time.sleep(delay)
            raw = self._read_until_prompt()
            return Elm327Response(
                command=normalized_command,
                raw=raw,
                lines=self._parse_lines(raw),
            )
        except OSError as exc:
            raise Elm327CommandError(
                f"ELM327 command failed: {normalized_command}: {exc}"
            ) from exc

    def _initialize(self) -> None:
        for command in self.INITIALIZATION_COMMANDS:
            self.send_command(command, delay=0.6)

    def _drain_input(self) -> None:
        if self._socket is None:
            return
        previous_timeout = self._socket.gettimeout()
        try:
            self._socket.setblocking(False)
            while True:
                try:
                    if not self._socket.recv(4096):
                        break
                except BlockingIOError:
                    break
        finally:
            self._socket.settimeout(previous_timeout)

    def _read_until_prompt(self) -> str:
        if self._socket is None:
            raise Elm327ConnectionError("ELM327 device is not connected")

        data = bytearray()
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            try:
                chunk = self._socket.recv(1024)
            except socket.timeout:
                continue
            if not chunk:
                raise Elm327ConnectionError("ELM327 TCP bridge disconnected")
            data.extend(chunk)
            if b">" in chunk:
                break
        return data.decode("ascii", errors="replace")

    @staticmethod
    def _parse_lines(raw: str) -> tuple[str, ...]:
        cleaned = raw.replace(">", "\r")
        return tuple(line.strip() for line in cleaned.splitlines() if line.strip())

    def __enter__(self) -> Elm327TcpDevice:
        self.connect()
        return self

    def __exit__(self, *_args: object) -> None:
        self.disconnect()
