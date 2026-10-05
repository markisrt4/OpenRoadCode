# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import subprocess
import threading
import unittest
from unittest.mock import Mock, patch

from services.common.termux_battery_monitor import TermuxBatteryMonitor, parse_battery, _read_battery
from ui.system_diagnostics import BatterySnapshot

PAYLOAD = {"present": True, "temperature": 30.1, "percentage": 77,
           "health": "GOOD", "status": "DISCHARGING", "plugged": "UNPLUGGED"}


class BatteryTests(unittest.TestCase):
    def test_real_api_units_and_labels(self):
        battery = parse_battery(PAYLOAD)
        self.assertEqual(battery.temperature_c, 30.1)
        self.assertEqual(battery.charge_percent, 77)
        self.assertEqual((battery.health, battery.charging_state, battery.plugged),
                         ("GOOD", "DISCHARGING", "UNPLUGGED"))
        self.assertEqual(battery.state, "available")

    def test_invalid_missing_and_nonfinite_values(self):
        for payload in (None, {}, {"error": "permission"}, {"present": False}):
            self.assertEqual(parse_battery(payload).state, "unavailable")
        for value in (True, float('nan'), float('inf'), '30.1', 10**1000):
            self.assertIsNone(parse_battery(dict(PAYLOAD, temperature=value)).temperature_c)
        self.assertIsNone(parse_battery(dict(PAYLOAD, percentage=101)).charge_percent)

    def test_linux_never_invokes_cli(self):
        reader = Mock()
        monitor = TermuxBatteryMonitor(enabled=False, reader=reader)
        monitor.start()
        monitor.close()
        reader.assert_not_called()
        self.assertEqual(monitor.snapshot().state, 'not_applicable')

    def test_stale_readings_lose_old_good_values(self):
        monitor = TermuxBatteryMonitor(enabled=True, monotonic=lambda: 66)
        monitor._sample = parse_battery(PAYLOAD)
        monitor._received = 0
        self.assertEqual(monitor.snapshot().state, 'unavailable')
        self.assertIsNone(monitor.snapshot().temperature_c)

    def test_timeout_is_bounded_and_missing_command_is_explained(self):
        with patch('services.common.termux_battery_monitor.shutil.which', return_value='/bin/termux-battery-status'), \
             patch('services.common.termux_battery_monitor.subprocess.run', side_effect=subprocess.TimeoutExpired('battery', 3)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                _read_battery()
            self.assertEqual(run.call_args.kwargs['timeout'], 3)
        with patch('services.common.termux_battery_monitor.shutil.which', return_value=None):
            with self.assertRaises(FileNotFoundError):
                _read_battery()

    def test_failed_read_recovers_and_worker_closes(self):
        ready = threading.Event()
        calls = 0
        def read():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise subprocess.TimeoutExpired('battery', 3)
            ready.set()
            return PAYLOAD
        monitor = TermuxBatteryMonitor(enabled=True, reader=read, interval_seconds=.01)
        try:
            monitor.start()
            monitor.start()
            self.assertTrue(ready.wait(1))
        finally:
            monitor.close()
        self.assertEqual(monitor.snapshot().temperature_c, 30.1)
        self.assertIsNone(monitor._thread)
