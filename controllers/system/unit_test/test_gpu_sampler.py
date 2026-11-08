"""Offline tests for Qualcomm KGSL busy counters."""
import tempfile
import unittest
from pathlib import Path
from controllers.system.gpu_sampler import GpuSampler


class GpuSamplerTests(unittest.TestCase):
    def test_busy_fraction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gpubusy"
            path.write_text("135032 1003426\n")
            usage, source = GpuSampler(path).sample()
            self.assertAlmostEqual(usage, 13.46, places=2)
            self.assertIn("KGSL", source)

    def test_zero_total_is_unavailable_not_zero_percent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gpubusy"
            path.write_text("0 0\n")
            usage, _ = GpuSampler(path).sample()
            self.assertIsNone(usage)

    def test_missing_counter_is_unavailable(self):
        usage, _ = GpuSampler(Path("/nonexistent/orc-gpu-test")).sample()
        self.assertIsNone(usage)


if __name__ == "__main__":
    unittest.main()
