# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for lightweight Linux system diagnostics sampling."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controllers.system.system_diagnostics_controller import SystemDiagnosticsController


class SystemDiagnosticsControllerTest(unittest.TestCase):
    def test_snapshot_reads_proc_sys_and_cpu_delta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / "proc"
            sys_root = root / "sys"
            (proc / "self").mkdir(parents=True)
            thermal = sys_root / "class" / "thermal" / "thermal_zone0"
            thermal.mkdir(parents=True)

            (proc / "stat").write_text(
                "cpu  100 0 100 800 0 0 0 0 0 0\n",
                encoding="utf-8",
            )
            (proc / "meminfo").write_text(
                "MemTotal:       1000000 kB\n"
                "MemAvailable:    250000 kB\n",
                encoding="utf-8",
            )
            (proc / "uptime").write_text("90061.5 0.0\n", encoding="utf-8")
            (proc / "self" / "status").write_text(
                "Name:\tpython\n"
                "VmRSS:\t20480 kB\n"
                "Threads:\t7\n",
                encoding="utf-8",
            )
            (thermal / "temp").write_text("70000\n", encoding="utf-8")

            controller = SystemDiagnosticsController(
                proc_root=proc,
                sys_root=sys_root,
                disk_path=root,
            )
            with (
                patch(
                    "controllers.system.system_diagnostics_controller.os.getloadavg",
                    return_value=(2.0, 1.5, 1.0),
                ),
                patch(
                    "controllers.system.system_diagnostics_controller.os.cpu_count",
                    return_value=4,
                ),
            ):
                first = controller.snapshot()
                self.assertIsNone(first.cpu_percent)

                (proc / "stat").write_text(
                    "cpu  200 0 200 900 0 0 0 0 0 0\n",
                    encoding="utf-8",
                )
                second = controller.snapshot()

            self.assertAlmostEqual(second.cpu_percent or 0.0, 66.666, places=2)
            self.assertEqual(second.load_1m, 2.0)
            self.assertEqual(second.cpu_count, 4)
            self.assertAlmostEqual(second.memory_used_percent or 0.0, 75.0)
            self.assertAlmostEqual(second.temperature_c or 0.0, 70.0)
            self.assertAlmostEqual(second.uptime_seconds or 0.0, 90061.5)
            self.assertAlmostEqual(second.process_rss_mb or 0.0, 20.0)
            self.assertEqual(second.process_threads, 7)
            self.assertIsNotNone(second.disk_used_percent)
            self.assertEqual(second.warnings, ())

    def test_thresholds_produce_health_warnings(self) -> None:
        warnings = SystemDiagnosticsController._warnings(
            cpu_percent=97.0,
            load_1m=8.0,
            cpu_count=4,
            memory_used_percent=94.0,
            disk_used_percent=93.0,
            temperature_c=84.0,
        )

        self.assertEqual(len(warnings), 5)
        self.assertTrue(any("temperature" in warning for warning in warnings))
        self.assertTrue(any("memory" in warning for warning in warnings))
        self.assertTrue(any("filesystem" in warning for warning in warnings))
        self.assertTrue(any("CPU saturation" in warning for warning in warnings))
        self.assertTrue(any("system load" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
