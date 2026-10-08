# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Resource attribution, process identity, and partial-visibility regression tests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controllers.system.orc_process_sampler import OrcProcessSampler, _classify


class OrcProcessSamplerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.now = 0.0
        self.sampler = OrcProcessSampler(self.root, monotonic=lambda: self.now, clock_ticks=100, page_size=4096)

    def tearDown(self):
        self.directory.cleanup()

    def process(self, pid, args, *, parent=1, start=100, ticks=100, rss=10, pss=20, io=100):
        root = self.root / str(pid)
        root.mkdir(exist_ok=True)
        fields = ["0"] * 22
        fields[0], fields[1], fields[11] = "S", str(parent), str(ticks)
        fields[13] = "99999"  # cumulative child CPU must not be counted
        fields[17], fields[19], fields[21] = "3", str(start), str(rss)
        (root / "stat").write_text(f"{pid} (a tricky ) process name) " + " ".join(fields))
        (root / "cmdline").write_bytes(b"\0".join(arg.encode() for arg in args) + b"\0")
        (root / "io").write_text(f"read_bytes: {io}\nwrite_bytes: {io * 2}\n")
        if pss is not None:
            (root / "smaps_rollup").write_text(f"Pss: {pss} kB\n")
        return root

    def test_roots_children_and_monitor_overhead_are_accounted_once(self):
        ui = ("python", "-m", "apps.orcUi")
        self.process(10, ui)
        self.process(11, ("chromium", "--renderer"), parent=10)
        self.process(12, ("python", "-m", "frontends.tk.system.component_test.performance_preview"))
        self.process(13, ("python", "-m", "unrelated"))
        self.sampler.sample()
        self.now = 2.0
        self.process(10, ui, ticks=200, io=300)
        self.process(11, ("chromium", "--renderer"), parent=10, ticks=150, io=200)
        self.process(12, ("python", "-m", "frontends.tk.system.component_test.performance_preview"), ticks=300)
        with patch("controllers.system.orc_process_sampler.os.cpu_count", return_value=4):
            sample = self.sampler.sample()
        self.assertEqual({p.pid for p in sample.processes}, {10, 11, 12})
        self.assertEqual(sample.process_count, 2)
        self.assertEqual(sample.cpu_percent, 75)
        self.assertEqual(sample.cpu_capacity_percent, 18.75)
        self.assertEqual(sample.rss_bytes, 20 * 4096)
        self.assertEqual(sample.pss_bytes, 40 * 1024)
        self.assertEqual(sample.read_bytes_per_second, 150)
        self.assertEqual(sample.write_bytes_per_second, 300)
        self.assertEqual(next(p for p in sample.processes if p.pid == 12).category, "diagnostics")

    def test_reused_pid_warms_up_instead_of_spiking_cpu_or_io(self):
        args = ("python", "-m", "services.navigation.navigation_service_cli")
        self.process(10, args, start=100, ticks=5000)
        self.sampler.sample()
        self.now = 1
        self.process(10, args, start=200, ticks=10)
        sample = self.sampler.sample()
        self.assertIsNone(sample.cpu_percent)
        self.assertIsNone(sample.read_bytes_per_second)
        self.now = 2
        self.process(10, args, start=200, ticks=20)
        self.assertEqual(self.sampler.sample().cpu_percent, 10)

    def test_reparented_child_remains_tracked_until_it_exits(self):
        self.process(10, ("python", "-m", "apps.orcUi"))
        self.process(11, ("chromium",), parent=10)
        self.sampler.sample()
        import shutil
        shutil.rmtree(self.root / "10")
        self.now = 1
        self.process(11, ("chromium",), parent=1)
        self.assertEqual([p.pid for p in self.sampler.sample().processes], [11])
        shutil.rmtree(self.root / "11")
        self.now = 2
        self.assertEqual(self.sampler.sample().process_count, 0)
        self.assertEqual(self.sampler._tracked, {})

    def test_denied_processes_and_metrics_are_not_reported_as_zero(self):
        args = ("python", "-m", "apps.orcUi")
        root = self.process(10, args, pss=None)
        (root / "io").unlink()
        self.process(11, ("python", "-m", "services.automotive.automotive_service_cli"))
        original = Path.read_bytes

        def read(path):
            if path.parent.name == "11":
                raise PermissionError()
            return original(path)

        with patch.object(Path, "read_bytes", read):
            sample = self.sampler.sample()
        self.assertEqual(sample.visibility, "partial")
        self.assertEqual(sample.process_count, 1)
        self.assertIsNone(sample.pss_bytes)
        self.assertIsNone(sample.read_bytes_per_second)
        self.assertIsNone(sample.cpu_percent)

    def test_cpu_not_clamped_to_one_core_and_resets_are_unavailable(self):
        args = ("python", "-m", "apps.orcUi")
        self.process(10, args)
        self.sampler.sample()
        self.now = 1
        self.process(10, args, ticks=350)
        self.assertEqual(self.sampler.sample().cpu_percent, 250)
        self.now = 2
        self.process(10, args, ticks=10, io=0)
        sample = self.sampler.sample()
        self.assertIsNone(sample.cpu_percent)
        self.assertIsNone(sample.read_bytes_per_second)

    def test_unrelated_modules_and_arguments_do_not_match_orc(self):
        for args in (("python", "-m", "apps.other"), ("bash", "-c", "python -m apps.orcUi"),
                     ("grep", "apps.orcUi"), ("python", "-m", "apps.orcUi_extra")):
            self.assertIsNone(_classify(args))
        self.assertEqual(_classify(("/opt/bin/openroadcode-map-renderer",)), ("Map renderer", "workload"))


if __name__ == "__main__":
    unittest.main()
