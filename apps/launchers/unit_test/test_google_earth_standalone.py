"""Keep standalone rendering diagnostics independent of existing Earth apps."""

import re
import unittest
from unittest.mock import Mock, patch

from apps.launchers.component_test.google_earth_launcher_cli import main


class GoogleEarthStandaloneTest(unittest.TestCase):
    def test_unique_profile_selector_and_cleanup_on_interruption(self):
        browser = Mock()
        with (
            patch("sys.argv", ["earth-test", "--display", ":1"]),
            patch("apps.launchers.component_test.google_earth_launcher_cli.BrowserKioskLauncher",
                  return_value=browser) as factory,
            patch("builtins.input", side_effect=KeyboardInterrupt),
            patch("builtins.print"),
            patch("apps.launchers.component_test.google_earth_launcher_cli.logging_file_path", return_value="test.log"),
        ):
            with self.assertRaises(KeyboardInterrupt):
                main()
        arguments = factory.call_args.kwargs
        self.assertEqual(arguments["process_pattern"], re.escape(arguments["profile_path"]))
        self.assertNotEqual(arguments["process_pattern"], "earth.google.com")
        self.assertEqual(arguments["window_position"], (0, 0))
        self.assertFalse(arguments["kiosk"])
        browser.launch.assert_called_once()
        browser.stop.assert_called_once()
        browser.set_url.assert_not_called()

    def test_gps_uses_separate_debugger_and_closes_subscriber_before_browser(self):
        browser, controller = Mock(), Mock()
        controller.tick.side_effect = KeyboardInterrupt
        lifecycle = Mock()
        lifecycle.attach_mock(browser, "browser")
        lifecycle.attach_mock(controller, "controller")
        with (
            patch("sys.argv", ["earth-test", "--orc-gps"]),
            patch("apps.launchers.component_test.google_earth_launcher_cli.BrowserKioskLauncher",
                  return_value=browser) as factory,
            patch("apps.launchers.component_test.google_earth_launcher_cli.EarthNavigationController",
                  return_value=controller),
            patch("builtins.print"),
            patch("apps.launchers.component_test.google_earth_launcher_cli.logging_file_path", return_value="test.log"),
        ):
            self.assertEqual(main(), 0)
        self.assertIn("--remote-debugging-port=9224", factory.call_args.kwargs["extra_arguments"])
        controller.start.assert_called_once()
        controller.tick.assert_called_once()
        controller.close.assert_called_once()
        calls = [call[0] for call in lifecycle.mock_calls]
        self.assertLess(calls.index("controller.close"), calls.index("browser.stop"))
