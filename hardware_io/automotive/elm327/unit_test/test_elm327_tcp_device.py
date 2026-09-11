# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for ELM327 TCP response framing."""

from __future__ import annotations

import unittest

from hardware_io.automotive.elm327.elm327_tcp_device import Elm327TcpDevice


class _FakeSocket:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    def recv(self, _size: int) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class Elm327TcpDeviceTest(unittest.TestCase):
    def test_ignores_leading_prompt_until_payload_arrives(self) -> None:
        device = Elm327TcpDevice(timeout=1.0)
        device._socket = _FakeSocket([b">", b"E804410C0A82", b">"])

        raw = device._read_until_prompt()

        self.assertEqual(raw, "E804410C0A82")

    def test_leading_prompt_and_payload_in_same_chunk(self) -> None:
        device = Elm327TcpDevice(timeout=1.0)
        device._socket = _FakeSocket([b">E804410C0A82>"])

        raw = device._read_until_prompt()

        self.assertEqual(raw, "E804410C0A82")


if __name__ == "__main__":
    unittest.main()
