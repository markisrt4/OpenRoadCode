# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Host telemetry cache, lifecycle, and authenticated HTTP contract checks."""

import threading
import unittest
from unittest.mock import Mock, patch

from services.common.system_performance_monitor import SystemPerformanceMonitor
from services.common.service_manager_pairing import ServiceManagerPairing
from services.linux.systemd_service_manager_http import SystemdServiceManagerHandler
from services.termux.service_manager_http import ServiceManagerHandler
from ui.system_diagnostics import SystemDiagnosticsSnapshot


class SystemPerformanceMonitorTest(unittest.TestCase):
    def test_snapshot_read_does_not_trigger_sampling_and_wire_units_are_si(self):
        controller = Mock()
        monitor = SystemPerformanceMonitor(controller)
        self.assertIsNone(monitor.payload()["snapshot"])
        self.assertIsNone(monitor.snapshot().cpu_percent)
        controller.snapshot.assert_not_called()
        sample = SystemDiagnosticsSnapshot(
            cpu_percent=42, cpu_frequency_mhz=2400, memory_total_mb=512,
            disk_free_gb=2, sampled_at_unix_s=123, temperature_c=55,
        )
        monitor._history.append(sample)
        payload = monitor.payload()
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["snapshot"]["cpu_frequency_hz"], 2400000000)
        self.assertEqual(payload["snapshot"]["memory_total_bytes"], 536870912)
        self.assertEqual(payload["snapshot"]["disk_free_bytes"], 2147483648)
        self.assertIsNone(payload["snapshot"]["swap_total_bytes"])
        self.assertNotIn("memory_total_mb", payload["snapshot"])
        self.assertEqual(set(payload["history"][0]), {
            "sampled_at_unix_s", "cpu_percent", "process_cpu_percent", "memory_used_percent", "temperature_c",
        })

    def test_worker_recovers_from_error_and_stops_without_leaking(self):
        recovered = threading.Event()
        controller = Mock()
        monitor = SystemPerformanceMonitor(controller, interval_seconds=0.01, history_samples=2)
        calls = 0

        def sample():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("temporary read failure")
            if calls >= 4:
                monitor._stop.set()
                recovered.set()
            return SystemDiagnosticsSnapshot(cpu_percent=calls, sampled_at_unix_s=calls)

        controller.snapshot.side_effect = sample
        try:
            monitor.start()
            monitor.start()
            self.assertTrue(recovered.wait(2))
        finally:
            monitor.close()
        self.assertIsNone(monitor._thread)
        self.assertEqual([s.cpu_percent for s in monitor.history()], [3, 4])
        self.assertIsNone(monitor.payload()["error"])
        self.assertIsNotNone(monitor.payload()["sample_age_seconds"])

    def test_invalid_configuration_is_rejected(self):
        for kwargs in ({"interval_seconds": 0}, {"history_samples": 0}):
            with self.assertRaises(ValueError):
                SystemPerformanceMonitor(**kwargs)


class PerformanceHttpContractTest(unittest.TestCase):
    def make_handler(self, handler_type, token=None):
        handler = object.__new__(handler_type)
        handler.path = "/performance"
        handler.client_address = ("192.0.2.25", 1234)
        handler.headers = {} if token is None else {"Authorization": "Bearer " + token}
        handler.auth_token = "admin"
        handler.pairing = ServiceManagerPairing()
        handler.performance_monitor = Mock()
        handler.performance_monitor.payload.return_value = {"version": 1, "snapshot": None, "history": []}
        handler._json = Mock()
        return handler

    def test_remote_metrics_require_authentication_on_both_platforms(self):
        for handler_type in (SystemdServiceManagerHandler, ServiceManagerHandler):
            for token in (None, "wrong"):
                with self.subTest(platform=handler_type.__name__, token=token):
                    handler = self.make_handler(handler_type, token)
                    handler.do_GET()
                    self.assertEqual(handler._json.call_args.args[0], 401)
                    handler.performance_monitor.payload.assert_not_called()

    def test_paired_client_can_read_cached_metrics_on_both_platforms(self):
        for handler_type in (SystemdServiceManagerHandler, ServiceManagerHandler):
            handler = self.make_handler(handler_type)
            pin, _ = handler.pairing.begin()
            _, token = handler.pairing.pair(pin, "Android test")
            handler.headers = {"Authorization": "Bearer " + token}
            handler.do_GET()
            self.assertEqual(handler._json.call_args.args[0], 200)
            handler.performance_monitor.payload.assert_called_once_with()

    def test_sampler_unavailable_is_explicit(self):
        handler = self.make_handler(SystemdServiceManagerHandler, "admin")
        handler.performance_monitor = None
        handler.do_GET()
        self.assertEqual(handler._json.call_args.args[0], 503)

    def test_unauthenticated_route_cannot_bypass_auth_with_query(self):
        handler = self.make_handler(SystemdServiceManagerHandler)
        handler.path = "/performance/?anything=1"
        handler.do_GET()
        self.assertEqual(handler._json.call_args.args[0], 401)
        handler.performance_monitor.payload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
