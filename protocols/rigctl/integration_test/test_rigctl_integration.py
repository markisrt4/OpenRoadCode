#!/usr/bin/env python3
"""Integration tests for RigctlClient over a real TCP socket."""

from __future__ import annotations

import threading
import unittest

from protocols.rigctl import RigctlClient
from protocols.rigctl.emulator.example_rigctl_server import ExampleRigctlServer


class RigctlClientIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ExampleRigctlServer(("127.0.0.1", 0))
        cls.thread = threading.Thread(
            target=cls.server.serve_forever,
            name="rigctl-component-server",
            daemon=True,
        )
        cls.thread.start()

        host, port = cls.server.server_address
        cls.client = RigctlClient(host=host, port=port, timeout=1.0)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2.0)

    def test_frequency_round_trip(self) -> None:
        self.assertEqual("RPRT 0", self.client.set_frequency(101_100_000))
        self.assertEqual("101100000", self.client.get_frequency())

    def test_mode_translation_and_server_state(self) -> None:
        self.assertEqual("RPRT 0", self.client.set_mode("NFM", 12_500))
        self.assertEqual("FM", self.server.state.mode)
        self.assertEqual(12_500, self.server.state.bandwidth_hz)

    def test_start_and_stop_extensions(self) -> None:
        self.assertEqual("RPRT 0", self.client.start())
        self.assertTrue(self.server.state.running)
        self.assertEqual("RPRT 0", self.client.stop())
        self.assertFalse(self.server.state.running)

    def test_level_queries(self) -> None:
        self.assertEqual("-73.0", self.client.get_signal_strength())
        self.assertEqual("18.5", self.client.get_snr())
        self.assertEqual(
            "OpenRoadCode Example Station",
            self.client.get_rds(),
        )

    def test_unknown_command_returns_protocol_error(self) -> None:
        self.assertEqual("RPRT -4", self.client.send("not-a-command"))

    def test_client_argument_validation(self) -> None:
        with self.assertRaises(ValueError):
            self.client.send("   ")
        with self.assertRaises(ValueError):
            self.client.set_frequency(0)
        with self.assertRaises(ValueError):
            self.client.set_mode("FM", -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
