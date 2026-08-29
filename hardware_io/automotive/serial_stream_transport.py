# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Serial byte-stream transport for automotive devices."""

from __future__ import annotations

import serial

from hardware_io.automotive.stream_transport_if import StreamTransportIf


class SerialStreamTransport(StreamTransportIf):
    """Expose a pyserial connection through the automotive stream contract."""

    def __init__(self, port: str, baud: int = 38400, timeout: float = 1.0) -> None:
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
        self._serial = serial.Serial(
            port=self._port,
            baudrate=self._baud,
            timeout=self._timeout,
        )

    def close(self) -> None:
        if self._serial is None:
            return
        try:
            self._serial.close()
        finally:
            self._serial = None

    def reset_input_buffer(self) -> None:
        if self._serial is None:
            raise OSError("serial transport is not connected")
        self._serial.reset_input_buffer()

    def write(self, data: bytes) -> int:
        if self._serial is None:
            raise OSError("serial transport is not connected")
        return self._serial.write(data)

    def flush(self) -> None:
        if self._serial is None:
            raise OSError("serial transport is not connected")
        self._serial.flush()

    def read(self, size: int) -> bytes:
        if self._serial is None:
            raise OSError("serial transport is not connected")
        return self._serial.read(size)
