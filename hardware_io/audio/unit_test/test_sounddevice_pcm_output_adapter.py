# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Audio adapter tests without a sound card or PortAudio installation."""

import unittest
from unittest.mock import Mock

import numpy as np

from hardware_io.audio.sounddevice_pcm_output_adapter import SounddevicePcmOutputAdapter


class SounddevicePcmOutputAdapterTest(unittest.TestCase):
    def setUp(self):
        self.stream = Mock()
        self.stream.write.return_value = False
        self.sd = Mock()
        self.sd.OutputStream.return_value = self.stream

    def test_open_prime_write_drain_close(self):
        output = SounddevicePcmOutputAdapter(
            sounddevice_module=self.sd, prime_ms=100, volume=0.5
        )
        output.open()
        self.assertEqual(self.stream.write.call_args_list[0].args[0].shape, (4800, 1))
        output.write(np.array([-2, 0, 2], dtype=np.float32))
        np.testing.assert_array_equal(
            self.stream.write.call_args_list[-1].args[0].ravel(),
            [-1, 0, 1]
        )
        output.drain()
        output.close()
        self.stream.close.assert_called_once()
        output.close()

    def test_rejects_invalid_pcm(self):
        output = SounddevicePcmOutputAdapter(
            sounddevice_module=self.sd, prime_ms=0
        )
        output.open()
        with self.assertRaises(ValueError):
            output.write(np.array([np.nan]))
        with self.assertRaises(ValueError):
            output.write(np.zeros((2, 2)))
        output.close()

    def test_stereo_output_preserves_left_and_right(self):
        output = SounddevicePcmOutputAdapter(
            sounddevice_module=self.sd, prime_ms=0, channels=2, volume=1.0
        )
        output.open()
        self.assertEqual(self.sd.OutputStream.call_args.kwargs["channels"], 2)
        pcm = np.array([[0.25, -0.5], [-0.25, 0.5]], dtype=np.float32)
        output.write(pcm)
        np.testing.assert_array_equal(self.stream.write.call_args.args[0], pcm)
        with self.assertRaises(ValueError):
            output.write(np.ones(10, dtype=np.float32))
        output.close()

    def test_requires_open(self):
        output = SounddevicePcmOutputAdapter(sounddevice_module=self.sd)
        with self.assertRaises(RuntimeError):
            output.write(np.zeros(10))

    def test_underflow_tracking(self):
        self.stream.write.return_value = True
        output = SounddevicePcmOutputAdapter(
            sounddevice_module=self.sd, prime_ms=0
        )
        output.open()
        output.write(np.zeros(10))
        self.assertEqual(output.underflows, 1)
        output.close()


if __name__ == "__main__":
    unittest.main()
