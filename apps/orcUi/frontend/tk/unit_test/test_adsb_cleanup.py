# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import unittest
from threading import Event
from unittest.mock import Mock
from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl


class AdsbCleanupTest(unittest.TestCase):
    def test_exit_does_not_wait_and_prevents_relaunch_during_cleanup(self):
        entered, release = Event(), Event()
        launcher = Mock()
        def stop(_display):
            entered.set()
            release.wait(2)
        launcher.stop.side_effect = stop
        adapter = OrcUiAdsbControl(launcher)
        try:
            adapter.stop(":1")
            self.assertTrue(entered.wait(2))
            self.assertTrue(adapter._stop_thread.is_alive())
            with self.assertRaisesRegex(RuntimeError, "still closing"):
                adapter.launch(":1")
            adapter.stop(":1")
            launcher.stop.assert_called_once_with(":1")
        finally:
            release.set()
            adapter._stop_thread.join(2)
        adapter.launch(":1")
        launcher.launch.assert_called_once_with(":1")
