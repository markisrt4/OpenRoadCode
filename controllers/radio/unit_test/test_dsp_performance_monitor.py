# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Deterministic DSP timing and steady-state throughput tests."""

import unittest

from controllers.radio.dsp_performance_monitor import DspPerformanceMonitor


class DspPerformanceMonitorTest(unittest.TestCase):
    def test_budget_and_recent_window(self):
        clock = [0.0]
        monitor = DspPerformanceMonitor(sample_rate_hz=1000,
                                        warmup_seconds=0, recent_blocks=2,
                                        clock=lambda: clock[0])
        clock[0] = 0.1
        monitor.record(samples=100, dsp_seconds=0.02)
        clock[0] = 0.2
        monitor.record(samples=100, dsp_seconds=0.12)
        clock[0] = 0.3
        monitor.record(samples=100, dsp_seconds=0.03)
        result = monitor.snapshot()
        self.assertEqual(result.blocks, 3)
        self.assertEqual(result.over_budget_blocks, 1)
        self.assertAlmostEqual(result.dsp_utilization, 0.5667, places=4)
        self.assertAlmostEqual(result.recent_dsp_utilization, 0.75, places=4)
        self.assertEqual(result.dsp_max_ms, 120)
        self.assertEqual(result.steady_blocks, 3)

    def test_warmup_exclusion(self):
        clock = [0.0]
        monitor = DspPerformanceMonitor(sample_rate_hz=1000,
                                        warmup_seconds=5, clock=lambda: clock[0])
        clock[0] = 1
        monitor.record(samples=100, dsp_seconds=0.02)
        self.assertIsNone(monitor.snapshot().steady_processing_msps)
        clock[0] = 6
        monitor.record(samples=100, dsp_seconds=0.02)
        clock[0] = 7
        result = monitor.snapshot()
        self.assertEqual(result.steady_blocks, 1)
        self.assertIsNotNone(result.steady_processing_msps)

    def test_rejects_invalid_data(self):
        monitor = DspPerformanceMonitor()
        with self.assertRaises(ValueError):
            monitor.record(samples=0, dsp_seconds=0.1)
        with self.assertRaises(ValueError):
            monitor.record(samples=100, dsp_seconds=-1)


if __name__ == "__main__":
    unittest.main()
