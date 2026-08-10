"""Tests for ADS-B dashboard launch behavior."""

import unittest
from unittest.mock import Mock, patch

from apps.launchers.adsb_launcher import ADSBLauncher


class AdsbLauncherTest(unittest.TestCase):
    @patch("apps.launchers.adsb_launcher.subprocess.run")
    def test_reachable_dashboard_opens_without_receiver_hardware(
        self,
        subprocess_run: Mock,
    ) -> None:
        launcher = ADSBLauncher()
        launcher.browser = Mock()
        launcher._readsb_is_running = Mock(return_value=False)
        launcher._dashboard_is_reachable = Mock(return_value=True)
        launcher._wait_for_readsb = Mock()
        status = Mock()

        launcher.launch(":0", status)

        launcher._wait_for_readsb.assert_not_called()
        launcher.browser.launch.assert_called_once_with(":0", status)
        self.assertTrue(
            any(
                "without live data" in call.args[0]
                for call in status.call_args_list
            )
        )


if __name__ == "__main__":
    unittest.main()
