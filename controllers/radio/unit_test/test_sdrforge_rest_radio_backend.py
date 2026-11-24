# SPDX-License-Identifier: MIT
"""Hardware-independent contract checks for the SDRForge REST radio adapter."""

from __future__ import annotations

import unittest
from urllib.error import URLError
from unittest.mock import patch

from controllers.radio.adapters.sdrforge_rest_radio_backend import SdrForgeRestRadioBackend


class SdrForgeRestRadioBackendTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = SdrForgeRestRadioBackend()

    def test_receiver_snapshot_maps_to_radio_contract(self) -> None:
        snapshot = {
            "frequency_hz": 104300000,
            "mode": "WFM",
            "bandwidth_hz": 200000,
            "signal_strength": -35.0,
            "snr": 24.0,
            "rds": "WOMC",
        }
        with patch.object(self.backend, "_request", return_value=snapshot) as request:
            self.assertEqual(self.backend.get_frequency(), 104300000)
            self.assertEqual(self.backend.get_signal_strength(), -35.0)
            self.assertEqual(self.backend.get_snr(), 24.0)
            self.assertEqual(self.backend.get_rds(), "WOMC")
        self.assertEqual(request.call_count, 4)

    def test_control_paths_match_sdrforge_v1(self) -> None:
        with patch.object(self.backend, "_request", return_value={"ok": True}) as request:
            self.backend.start()
            self.backend.set_frequency(94700000)
            self.backend.set_mode("wfm", 200000)
            self.backend.stop()
        self.assertEqual(
            [call.args for call in request.call_args_list],
            [
                ("/v1/receiver/start", {}),
                ("/v1/receiver/frequency", {"frequency_hz": 94700000}),
                ("/v1/receiver/mode", {"mode": "WFM", "bandwidth_hz": 200000}),
                ("/v1/receiver/stop", {}),
            ],
        )

    def test_transient_read_reconnects_once(self) -> None:
        failure = RuntimeError("connection lost")
        failure.__cause__ = URLError("refused")
        with patch.object(
            self.backend, "_request_once", side_effect=[failure, {"frequency_hz": 94700000}]
        ) as request:
            with patch.object(self.backend, "wait_until_ready") as ready:
                self.assertEqual(self.backend.get_frequency(), 94700000)
        ready.assert_called_once_with(timeout=3.0)
        self.assertEqual(request.call_count, 2)

    def test_mutation_is_never_replayed_after_connection_loss(self) -> None:
        failure = RuntimeError("connection lost")
        failure.__cause__ = URLError("refused")
        with patch.object(self.backend, "_request_once", side_effect=failure) as request:
            with patch.object(self.backend, "wait_until_ready") as ready:
                with self.assertRaises(RuntimeError):
                    self.backend.set_frequency(94700000)
        request.assert_called_once()
        ready.assert_not_called()

    def test_health_returns_false_when_server_is_offline(self) -> None:
        with patch.object(self.backend, "_request_once", side_effect=RuntimeError("offline")):
            self.assertFalse(self.backend.health())

    def test_malformed_read_is_not_replayed(self) -> None:
        failure = RuntimeError("invalid JSON")
        failure.__cause__ = ValueError("invalid")
        with patch.object(self.backend, "_request_once", side_effect=failure) as request:
            with patch.object(self.backend, "wait_until_ready") as ready:
                with self.assertRaises(RuntimeError):
                    self.backend.receiver_status()
        request.assert_called_once()
        ready.assert_not_called()

    def test_diagnostics_initial_state(self) -> None:
        diagnostics = self.backend.connection_diagnostics()
        self.assertEqual(diagnostics.state, "unknown")
        self.assertEqual(diagnostics.reconnect_attempts, 0)
        self.assertIsNone(diagnostics.last_success_monotonic)

    def test_diagnostics_record_successful_reconnection(self) -> None:
        failure = RuntimeError("connection lost")
        failure.__cause__ = URLError("refused")
        with patch.object(
            self.backend, "_request_once", side_effect=[failure, {"frequency_hz": 94700000}]
        ):
            with patch.object(self.backend, "wait_until_ready"):
                self.backend.get_frequency()
        diagnostics = self.backend.connection_diagnostics()
        self.assertEqual(diagnostics.reconnect_attempts, 1)
        self.assertEqual(diagnostics.reconnect_successes, 1)

    def test_diagnostics_track_failed_reconnection(self) -> None:
        failure = RuntimeError("connection lost")
        failure.__cause__ = URLError("refused")
        with patch.object(self.backend, "_request_once", side_effect=failure):
            with patch.object(
                self.backend, "wait_until_ready", side_effect=RuntimeError("not ready")
            ):
                with self.assertRaises(RuntimeError):
                    self.backend.receiver_status()
        diagnostics = self.backend.connection_diagnostics()
        self.assertEqual(diagnostics.state, "unavailable")
        self.assertEqual(diagnostics.reconnect_attempts, 1)
        self.assertEqual(diagnostics.reconnect_successes, 0)
        self.assertEqual(diagnostics.last_error, "not ready")

    def test_invalid_frequency_does_not_call_service(self) -> None:
        with patch.object(self.backend, "_request") as request:
            with self.assertRaises(ValueError):
                self.backend.set_frequency(0)
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
