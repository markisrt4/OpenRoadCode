# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import unittest
from threading import Event
from unittest.mock import Mock, patch
from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl


class AdsbCleanupTest(unittest.TestCase):
    def test_termux_keeps_software_webgl_enabled(self):
        with patch("apps.orcUi.adapters.adsb_control.ApplicationsConfigParser") as parser, \
             patch("apps.orcUi.adapters.adsb_control.ADSBLauncher") as launcher, \
             patch("apps.orcUi.adapters.adsb_control._is_termux", return_value=True):
            parser.return_value.load.return_value.app.return_value.url = "http://127.0.0.1:8081/"
            launcher.return_value.browser.extra_arguments = ()
            OrcUiAdsbControl()
            flags = launcher.return_value.browser.extra_arguments
        self.assertIn("--use-angle=swiftshader", flags)
        self.assertIn("--disable-gpu-compositing", flags)
        self.assertNotIn("--disable-gpu", flags)

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
