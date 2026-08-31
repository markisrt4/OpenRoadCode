# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Byte-stream transport contract for automotive devices."""

from __future__ import annotations

from abc import ABC, abstractmethod


class StreamTransportIf(ABC):
    """Provide a connected bidirectional byte stream."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the transport is connected.

        @return True when the transport is connected; otherwise False.
        """
        ...

    @abstractmethod
    def connect(self) -> None:
        """Connect the transport."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the transport."""
        ...

    @abstractmethod
    def reset_input_buffer(self) -> None:
        """Discard unread input bytes already waiting on the transport."""
        ...

    @abstractmethod
    def write(self, data: bytes) -> int:
        """Write bytes to the transport.

        @param data Bytes to write.
        @return Number of bytes accepted by the transport.
        """
        ...

    @abstractmethod
    def flush(self) -> None:
        """Flush pending output when the transport requires it."""
        ...

    @abstractmethod
    def read(self, size: int) -> bytes:
        """Read bytes from the transport.

        @param size Maximum number of bytes to read.
        @return Up to ``size`` bytes, or empty bytes on timeout.
        """
        ...
