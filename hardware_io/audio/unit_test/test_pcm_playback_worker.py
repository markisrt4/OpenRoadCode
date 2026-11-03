# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Playback worker tests with an injected fake PCM device."""

import threading
import time
import unittest
from unittest.mock import Mock

import numpy as np

from hardware_io.audio.pcm_playback_worker import PcmPlaybackWorker


def wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


class PcmPlaybackWorkerTest(unittest.TestCase):
    def setUp(self):
        self.output = Mock()
        self.worker = PcmPlaybackWorker(self.output, queue_blocks=2)

    def tearDown(self):
        if self.worker.status.running:
            self.worker.stop()

    def test_routes_only_selected_channel(self):
        self.worker.select_channel("fm")
        self.worker.start()
        self.assertFalse(self.worker.submit("weather", np.ones(64)))
        self.assertTrue(self.worker.submit("fm", np.ones(64)))
        self.assertTrue(wait_until(lambda: self.worker.status.played_blocks == 1))
        self.worker.stop()
        self.output.open.assert_called_once_with(48_000)
        self.output.write.assert_called_once()
        self.output.close.assert_called_once()

    def test_switch_discards_queued_pcm(self):
        gate = threading.Event()
        entered = threading.Event()

        def blocking_write(_):
            entered.set()
            gate.wait(timeout=2.0)

        self.output.write.side_effect = blocking_write
        self.worker.select_channel("fm")
        self.worker.start()
        self.assertTrue(self.worker.submit("fm", np.ones(32)))
        self.assertTrue(entered.wait(1.0))
        self.assertTrue(self.worker.submit("fm", np.ones(32)))
        self.worker.select_channel("weather")
        self.assertTrue(self.worker.submit("weather", np.ones(32)))
        gate.set()
        self.assertTrue(wait_until(lambda: self.worker.status.played_blocks == 2))
        self.worker.stop()
        self.assertEqual(self.output.write.call_count, 2)

    def test_full_queue_drops_without_blocking(self):
        gate = threading.Event()
        entered = threading.Event()

        def blocking_write(_):
            entered.set()
            gate.wait(timeout=2.0)

        self.output.write.side_effect = blocking_write
        self.worker.select_channel("fm")
        self.worker.start()
        self.assertTrue(self.worker.submit("fm", np.ones(32)))
        self.assertTrue(entered.wait(1.0))
        self.assertTrue(self.worker.submit("fm", np.ones(32)))
        self.assertTrue(self.worker.submit("fm", np.ones(32)))
        self.assertFalse(self.worker.submit("fm", np.ones(32)))
        self.assertEqual(self.worker.status.dropped_blocks, 1)
        gate.set()
        self.worker.stop()

    def test_output_error_is_reported(self):
        self.output.write.side_effect = RuntimeError("audio device disconnected")
        self.worker.select_channel("fm")
        self.worker.start()
        self.assertTrue(self.worker.submit("fm", np.ones(32)))
        self.assertTrue(wait_until(lambda: self.worker.status.last_error is not None))
        self.assertIn("disconnected", self.worker.status.last_error)
        self.worker.stop()

    def test_requires_positive_queue_size(self):
        with self.assertRaises(ValueError):
            PcmPlaybackWorker(self.output, queue_blocks=0)


if __name__ == "__main__":
    unittest.main()
