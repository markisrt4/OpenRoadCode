# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Hardware-independent fractional RDS timing recovery tests."""

import unittest

import numpy as np

from controllers.radio.dsp.rds_symbol_timing_recovery import RdsSymbolTimingRecovery


def synthetic_symbols(count=36_000):
    rng = np.random.default_rng(4961)
    bits = rng.choice([-1.0, 1.0], size=5_000)
    t = np.arange(count) * 1187.5 / 12_000
    # Smooth symbol boundaries, as expected after an RDS matched filter.
    centers = np.arange(len(bits)) + 0.5
    return np.interp(t, centers, bits, left=bits[0], right=bits[-1]).astype(np.complex64)


class RdsSymbolTimingRecoveryTest(unittest.TestCase):
    def test_fractional_output_rate(self):
        recovered = RdsSymbolTimingRecovery().process(synthetic_symbols())
        self.assertLess(abs(len(recovered) - 3562), 4)
        self.assertTrue(np.all(np.isfinite(recovered)))
        self.assertTrue(np.iscomplexobj(recovered))

    def test_irregular_streaming_matches_whole_block(self):
        samples = synthetic_symbols(32_137)
        expected = RdsSymbolTimingRecovery().process(samples)
        recovery = RdsSymbolTimingRecovery()
        chunks = [recovery.process(samples[i:i + 137])
                  for i in range(0, len(samples), 137)]
        np.testing.assert_allclose(np.concatenate(chunks), expected, atol=1e-6)

    def test_reset_restarts_symbol_clock(self):
        samples = synthetic_symbols(12_000)
        recovery = RdsSymbolTimingRecovery()
        expected = recovery.process(samples)
        recovery.process(samples)
        recovery.reset()
        np.testing.assert_allclose(recovery.process(samples), expected, atol=1e-6)

    def test_rejects_invalid_input(self):
        recovery = RdsSymbolTimingRecovery()
        for samples in (np.ones(10), np.ones((2, 2), dtype=np.complex64),
                        np.array([complex(np.inf, 0)])):
            with self.assertRaises(ValueError):
                recovery.process(samples)
        with self.assertRaises(ValueError):
            RdsSymbolTimingRecovery(timing_gain=0)
        self.assertEqual(recovery.process(np.array([], dtype=np.complex64)).size, 0)


if __name__ == "__main__":
    unittest.main()
