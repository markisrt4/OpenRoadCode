from __future__ import annotations

import time

import serial

from hardware_io.automotive.obd2.obd2_adapter import Obd2Adapter
from hardware_io.automotive.obd2.obd2_errors import (
    Obd2CommandError,
    Obd2ConnectionError,
)
from hardware_io.automotive.obd2.obd2_response import Obd2Response


class Elm327Adapter(Obd2Adapter):
    """
    OBD-II adapter implementation for ELM327-compatible serial devices.
    """

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

        except (serial.SerialException, OSError) as exc:
            self.disconnect()

            raise Obd2ConnectionError(
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
        delay: float = 0.25,
    ) -> Obd2Response:
        if not self.is_connected or self._serial is None:
            raise Obd2ConnectionError(
                "ELM327 adapter is not connected"
            )

        normalized_command = command.strip().upper()

        if not normalized_command:
            raise ValueError("command cannot be empty")

        try:
            self._serial.reset_input_buffer()
            self._serial.write(
                f"{normalized_command}\r".encode("ascii")
            )
            self._serial.flush()

            if delay > 0:
                time.sleep(delay)

            raw = self._read_until_prompt()

            return Obd2Response(
                command=normalized_command,
                raw=raw,
                lines=self._parse_lines(raw),
            )

        except (serial.SerialException, OSError) as exc:
            raise Obd2CommandError(
                f"OBD-II command failed: {normalized_command}"
            ) from exc

    def _initialize(self) -> None:
        for command in self.INITIALIZATION_COMMANDS:
            self.send_command(command, delay=0.6)

    def _read_until_prompt(self) -> str:
        if self._serial is None:
            raise Obd2ConnectionError(
                "ELM327 adapter is not connected"
            )

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
        lines: list[str] = []

        for line in raw.replace(">", "").splitlines():
            cleaned = line.strip()

            if cleaned:
                lines.append(cleaned)

        return tuple(lines)

    def __enter__(self) -> Elm327Adapter:
        self.connect()
        return self

    def __exit__(self, *_args: object) -> None:
        self.disconnect()
