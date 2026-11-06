# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest
from unittest.mock import patch

from hardware_io.automotive.elm327.elm327_errors import Elm327CommandError
from hardware_io.automotive.elm327.elm327_tcp_device import Elm327TcpDevice


class _Socket:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.sent = []
        self.closed = False

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, _size):
        return next(self.chunks, b">")

    def close(self):
        self.closed = True


class ElmMonitorCaptureTest(unittest.TestCase):
    def _device(self, chunks):
        device = Elm327TcpDevice()
        fake = _Socket(chunks)
        device._socket = fake
        device._drain_input = lambda: None
        return device, fake

    def test_monitor_prompt_returns_capture(self):
        device, fake = self._device([b"153 01 02\\r>"])
        result = device.capture_monitor()
        self.assertTrue(result.prompt_recovered)
        self.assertIn("153 01 02", result.raw)
        self.assertEqual(fake.sent, [b"ATMA\\r"])

    def test_byte_limit_stops_monitor(self):
        device, fake = self._device([b"12345678", b">"])
        result = device.capture_monitor(max_bytes=8)
        self.assertTrue(result.byte_limit_reached)
        self.assertEqual(fake.sent, [b"ATMA\\r", b"\\r"])

    def test_unrecovered_monitor_disconnects(self):
        device, fake = self._device([b"1234"])
        with patch("hardware_io.automotive.elm327.elm327_tcp_device.time.monotonic", side_effect=[0.0, 0.0, 0.0, 1.0, 1.0, 4.0]):
            with self.assertRaises(Elm327CommandError):
                device.capture_monitor(duration_seconds=0.5, recovery_seconds=1.0)
        self.assertTrue(fake.closed)
        self.assertFalse(device.is_connected)


if __name__ == "__main__":
    unittest.main()
