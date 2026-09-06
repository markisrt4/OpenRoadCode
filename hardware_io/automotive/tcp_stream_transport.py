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
        sock = socket.create_connection(
            (self._host, self._port), timeout=self._timeout
        )
        sock.settimeout(self._timeout)
        self._socket = sock

    def close(self) -> None:
        sock = self._socket
        self._socket = None
        if sock is not None:
            sock.close()

    def reset_input_buffer(self) -> None:
        sock = self._require_socket()
        previous_timeout = sock.gettimeout()
        try:
            sock.setblocking(False)
            while True:
                try:
                    data = sock.recv(4096)
                    if not data:
                        self._mark_disconnected(sock)
                        raise OSError("TCP transport peer disconnected")
                except BlockingIOError:
                    break
        except OSError:
            if self._socket is sock:
                self._mark_disconnected(sock)
            raise
        finally:
            if self._socket is sock:
                sock.settimeout(previous_timeout)

    def write(self, data: bytes) -> int:
        sock = self._require_socket()
        try:
            sock.sendall(data)
        except OSError:
            self._mark_disconnected(sock)
            raise
        return len(data)

    def flush(self) -> None:
        # TCP sendall() has already handed the complete buffer to the socket.
        return

    def read(self, size: int) -> bytes:
        sock = self._require_socket()
        try:
            data = sock.recv(size)
        except socket.timeout:
            return b""
        except OSError:
            self._mark_disconnected(sock)
            raise
        if not data:
            self._mark_disconnected(sock)
            raise OSError("TCP transport peer disconnected")
        return data

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            raise OSError("TCP transport is not connected")
        return self._socket

    def _mark_disconnected(self, sock: socket.socket) -> None:
        if self._socket is sock:
            self._socket = None
        try:
            sock.close()
        except OSError:
            pass
