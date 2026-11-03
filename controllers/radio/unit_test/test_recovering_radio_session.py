# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Hardware-free recovery state machine tests."""

import unittest

from controllers.radio.recovering_radio_session import RecoveringRadioSession


class _Session:
    def __init__(self, *, start_error=False, read_error=False):
        self.start_error = start_error
        self.read_error = read_error
        self.stopped = False

    def start(self):
        if self.start_error:
            raise OSError("USB missing")

    def stop(self):
        self.stopped = True

    def process_once(self):
        if self.read_error:
            raise OSError("USB disconnected")
        return {"ok": True}


class RecoveringRadioSessionTest(unittest.TestCase):
    def test_reconnect_after_read_failure(self):
        first = _Session(read_error=True)
        second = _Session()
        pending = iter([first, second])
        recovery = RecoveringRadioSession(lambda: next(pending),
                                          max_retries=1, sleep=lambda _: None)
        recovery.start()
        self.assertIsNone(recovery.process_once())
        self.assertTrue(first.stopped)
        self.assertEqual(recovery.status.state, "CONNECTED")
        self.assertEqual(recovery.status.successful_reconnects, 1)
        self.assertEqual(recovery.status.reconnect_attempts, 2)
        self.assertEqual(recovery.process_once(), {"ok": True})
        recovery.stop()
        self.assertTrue(second.stopped)

    def test_start_retry_and_exhaustion(self):
        sessions = []
        def factory():
            session = _Session(start_error=True)
            sessions.append(session)
            return session
        recovery = RecoveringRadioSession(factory, max_retries=2,
                                          sleep=lambda _: None)
        with self.assertRaisesRegex(RuntimeError, "exhausted"):
            recovery.start()
        self.assertEqual(recovery.status.state, "FAILED")
        self.assertEqual(recovery.status.reconnect_attempts, 3)
        self.assertTrue(all(s.stopped for s in sessions))

    def test_initial_start_retry_succeeds(self):
        first = _Session(start_error=True)
        second = _Session()
        pending = iter([first, second])
        recovery = RecoveringRadioSession(lambda: next(pending),
                                          max_retries=1, sleep=lambda _: None)
        recovery.start()
        self.assertEqual(recovery.status.state, "CONNECTED")
        self.assertTrue(first.stopped)
        self.assertEqual(recovery.status.successful_reconnects, 1)
        recovery.stop()


if __name__ == "__main__":
    unittest.main()
