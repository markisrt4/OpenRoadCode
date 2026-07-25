from __future__ import annotations

import time

import serial

from hardware_io.automotive.elm327.elm327_errors import (
    Elm327CommandError,
    Elm327ConnectionError,
)
from hardware_io.automotive.elm327.elm327_response import Elm327Response


class Elm327Device:
    """Serial connection to an ELM327-compatible device."""

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
    ) -> None:
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._serial: serial.Serial | None = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def connect(self) -> None:
        if self.is_connected:
            return

        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baud,
                timeout=self._timeout,
            )
            self._initialize()
        except Elm327CommandError as exc:
            self.disconnect()
            raise Elm327ConnectionError(
                f"Connected to {self._port}, but ELM327 initialization "
                f"failed: {exc}"
            ) from exc
        except (serial.SerialException, OSError) as exc:
            self.disconnect()
            raise Elm327ConnectionError(
                f"Unable to connect to ELM327 on {self._port}. "
                "Check adapter power, rfcomm, Bluetooth connectivity, "
                "and whether another application is using the device."
            ) from exc

    def disconnect(self) -> None:
        if self._serial is None:
            return

        try:
            self._serial.close()
        finally:
            self._serial = None

    def send_command(
        self,
        command: str,
        delay: float = 0.0,
    ) -> Elm327Response:
        if not self.is_connected or self._serial is None:
            raise Elm327ConnectionError("ELM327 device is not connected")

        normalized_command = command.strip().upper()
        if not normalized_command:
            raise ValueError("command cannot be empty")

        try:
            self._serial.reset_input_buffer()
            self._serial.write(f"{normalized_command}\r".encode("ascii"))
            self._serial.flush()

            if delay > 0:
                time.sleep(delay)

            raw = self._read_until_prompt()
            return Elm327Response(
                command=normalized_command,
                raw=raw,
                lines=self._parse_lines(raw),
            )
        except (serial.SerialException, OSError) as exc:
            raise Elm327CommandError(
                f"ELM327 command failed: {normalized_command}: {exc}"
            ) from exc

    def _initialize(self) -> None:
        for command in self.INITIALIZATION_COMMANDS:
            self.send_command(command, delay=0.6)

    def _read_until_prompt(self) -> str:
        if self._serial is None:
            raise Elm327ConnectionError("ELM327 device is not connected")

        data = bytearray()
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            chunk = self._serial.read(1)
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
