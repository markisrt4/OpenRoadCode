# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import time

from hardware_io.automotive.serial_stream_transport import SerialStreamTransport
from hardware_io.automotive.stream_transport_if import StreamTransportIf
from hardware_io.automotive.elm327.elm327_errors import (
    Elm327CommandError,
    Elm327ConnectionError,
)
from hardware_io.automotive.elm327.elm327_response import Elm327Response


class Elm327Device:
    """Command interface to an ELM327-compatible byte-stream device."""

    INITIALIZATION_COMMANDS = (
        "ATZ",
        "ATE0",
        "ATL0",
        "ATS0",
        "ATH1",
        "ATSP0",
    )

    def __init__(
        self,
        port: str = "/dev/rfcomm0",
        baud: int = 38400,
        timeout: float = 1.0,
        *,
        transport: StreamTransportIf | None = None,
    ) -> None:
        self._port = port
        self._timeout = timeout
        self._transport = transport or SerialStreamTransport(
            port=port,
            baud=baud,
            timeout=timeout,
        )

    @property
    def is_connected(self) -> bool:
        return self._transport.is_connected

    def connect(self) -> None:
        if self.is_connected:
            return

        try:
            self._transport.connect()
            self._initialize()
        except Elm327CommandError as exc:
            self.disconnect()
            raise Elm327ConnectionError(
                f"Connected to {self._port}, but ELM327 initialization "
                f"failed: {exc}"
            ) from exc
        except OSError as exc:
            self.disconnect()
            raise Elm327ConnectionError(
                f"Unable to connect to ELM327 on {self._port}: {exc}"
            ) from exc

    def disconnect(self) -> None:
        self._transport.close()

    def send_command(
        self,
        command: str,
        delay: float = 0.0,
    ) -> Elm327Response:
        if not self.is_connected:
            raise Elm327ConnectionError("ELM327 device is not connected")

        normalized_command = command.strip().upper()
        if not normalized_command:
            raise ValueError("command cannot be empty")

        try:
            self._transport.reset_input_buffer()
            self._transport.write(f"{normalized_command}\r".encode("ascii"))
            self._transport.flush()

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

    def _read_until_prompt(self) -> str:
        if not self.is_connected:
            raise Elm327ConnectionError("ELM327 device is not connected")

        data = bytearray()
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            chunk = self._transport.read(1)
            if not chunk:
                continue
            data.extend(chunk)
            if chunk == b">":
                break

        return data.decode("ascii", errors="replace")

    @staticmethod
    def _parse_lines(raw: str) -> tuple[str, ...]:
        return tuple(
            line.strip()
            for line in raw.replace(">", "").splitlines()
            if line.strip()
        )

    def __enter__(self) -> Elm327Device:
        self.connect()
        return self

    def __exit__(self, *_args: object) -> None:
        self.disconnect()
