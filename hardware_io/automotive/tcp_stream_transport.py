# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""TCP byte-stream transport for Android and network device bridges."""

from __future__ import annotations

import socket

from hardware_io.automotive.stream_transport_if import StreamTransportIf


class TcpStreamTransport(StreamTransportIf):
    """Expose a TCP connection through the automotive stream contract."""

    def __init__(self, host: str, port: int, timeout: float = 1.0) -> None:
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
        self._socket = socket.create_connection(
            (self._host, self._port), timeout=self._timeout
        )
        self._socket.settimeout(self._timeout)

    def close(self) -> None:
        if self._socket is None:
            return
        try:
            self._socket.close()
        finally:
            self._socket = None

    def reset_input_buffer(self) -> None:
        if self._socket is None:
            raise OSError("TCP transport is not connected")
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

    def write(self, data: bytes) -> int:
        if self._socket is None:
            raise OSError("TCP transport is not connected")
        self._socket.sendall(data)
        return len(data)

    def flush(self) -> None:
        # TCP sendall() has already handed the complete buffer to the socket.
        return

    def read(self, size: int) -> bytes:
        if self._socket is None:
            raise OSError("TCP transport is not connected")
        try:
            return self._socket.recv(size)
        except socket.timeout:
            return b""
