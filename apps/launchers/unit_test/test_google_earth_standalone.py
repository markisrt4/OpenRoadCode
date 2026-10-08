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
