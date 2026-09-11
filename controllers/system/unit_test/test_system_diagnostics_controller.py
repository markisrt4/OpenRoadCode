# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Raspberry Pi performance sampling."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controllers.system.system_diagnostics_controller import SystemDiagnosticsController


class SystemDiagnosticsControllerTest(unittest.TestCase):
    def test_snapshot_reads_live_performance_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / "proc"
            sys_root = root / "sys"
            proc.mkdir()

            thermal = sys_root / "class" / "thermal" / "thermal_zone0"
            thermal.mkdir(parents=True)
            frequency = (
                sys_root
                / "devices"
                / "system"
                / "cpu"
                / "cpu0"
                / "cpufreq"
                / "scaling_cur_freq"
            )
            frequency.parent.mkdir(parents=True)

            (proc / "stat").write_text(
                "cpu 100 0 100 800 0 0 0 0 0 0\n"
                "cpu0 25 0 25 200 0 0 0 0 0 0\n",
                encoding="utf-8",
            )
            (proc / "meminfo").write_text(
                "MemTotal: 1000000 kB\n"
                "MemAvailable: 250000 kB\n"
                "SwapTotal: 100000 kB\n"
                "SwapFree: 90000 kB\n",
                encoding="utf-8",
            )
            (proc / "uptime").write_text("90061.5 0.0\n", encoding="utf-8")
            (thermal / "temp").write_text("70000\n", encoding="utf-8")
            frequency.write_text("2400000\n", encoding="utf-8")

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
                patch.object(
                    controller,
                    "_read_throttled_flags",
                    return_value="0x0",
                ),
            ):
                first = controller.snapshot()
                self.assertIsNone(first.cpu_percent)

                (proc / "stat").write_text(
                    "cpu 200 0 200 900 0 0 0 0 0 0\n"
                    "cpu0 50 0 50 225 0 0 0 0 0 0\n",
                    encoding="utf-8",
                )
                second = controller.snapshot()

            self.assertAlmostEqual(second.cpu_percent or 0.0, 66.666, places=2)
            self.assertEqual(len(second.per_core_percent), 1)
            self.assertEqual(second.cpu_count, 4)
            self.assertEqual(second.load_1m, 2.0)
            self.assertEqual(second.cpu_frequency_mhz, 2400.0)

            self.assertAlmostEqual(second.memory_used_percent or 0.0, 75.0)
            self.assertAlmostEqual(second.memory_available_mb or 0.0, 244.14, places=1)
            self.assertAlmostEqual(second.swap_used_mb or 0.0, 9.77, places=1)

            self.assertAlmostEqual(second.temperature_c or 0.0, 70.0)
            self.assertAlmostEqual(second.thermal_headroom_c or 0.0, 15.0)
            self.assertEqual(second.throttled_flags, "0x0")
            self.assertAlmostEqual(second.uptime_seconds or 0.0, 90061.5)

            self.assertIsNotNone(second.disk_used_percent)
            self.assertIsNotNone(second.disk_free_gb)
            self.assertIsNotNone(second.disk_total_gb)


if __name__ == "__main__":
    unittest.main()
