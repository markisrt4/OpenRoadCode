# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from unittest.mock import Mock
from types import SimpleNamespace

from apps.launchers.google_earth_launcher import GoogleEarthLauncher


class GoogleEarthPreloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.browser = Mock()
        self.browser.extra_arguments = ()
        self.browser.is_running.return_value = False
        self.browser.hide.return_value = True
        self.launcher = GoogleEarthLauncher(browser=self.browser)

    def test_earth_keeps_chromium_default_gpu_backend(self) -> None:
        self.assertFalse(any(argument.startswith(("--use-gl=", "--use-angle="))
                             for argument in self.browser.extra_arguments))

    def test_explicit_gpu_choice_is_preserved(self) -> None:
        self.browser.extra_arguments = ("--use-angle=vulkan",)
        GoogleEarthLauncher(browser=self.browser)
        self.assertIn("--use-angle=vulkan", self.browser.extra_arguments)
        self.assertNotIn("--use-angle=gl", self.browser.extra_arguments)

    def test_prepare_starts_and_hides_browser(self) -> None:
        launched_urls = []
        self.browser.launch.side_effect = lambda *args: launched_urls.append(self.browser.url)
        original_url = self.browser.url
        self.launcher.prepare(":1")
        self.assertEqual(launched_urls, ["about:blank"])
        self.assertEqual(self.browser.url, original_url)
        self.browser.launch.assert_called_once_with(":1", None)
        self.browser.hide.assert_called_once_with(":1", None)
        self.browser.stop.assert_not_called()

    def test_prepare_reuses_running_browser(self) -> None:
        self.browser.is_running.return_value = True
        self.launcher.prepare(":1")
        self.browser.launch.assert_not_called()
        self.browser.hide.assert_called_once_with(":1", None)

    def test_failed_hide_is_reported(self) -> None:
        self.browser.hide.return_value = False
        with self.assertRaisesRegex(RuntimeError, "could not hide"):
            self.launcher.prepare(":1")

    def test_warm_browser_can_be_shown_without_relaunch(self) -> None:
        self.browser.is_running.return_value = True
        self.browser.show.return_value = True
        self.assertTrue(self.launcher.show(":1"))
        self.browser.show.assert_called_once_with(":1", None)
        self.browser.launch.assert_not_called()

    def test_location_is_delegated_to_browser(self) -> None:
        self.launcher.set_location(42.0, -83.0)
        self.browser.set_url.assert_called_once_with(
            GoogleEarthLauncher._location_url(42.0, -83.0)
        )

    def test_show_of_prepared_shell_loads_earth_for_nonembedded_clients(self):
        self.launcher.prepare(":1")
        self.launcher._devtools = Mock()
        target = SimpleNamespace(url="about:blank")
        self.launcher._devtools.targets.return_value = [target]
        self.launcher._devtools.command.return_value = {}
        self.launcher.show(":1")
        self.launcher._devtools.command.assert_called_once_with(
            target, "Page.navigate", {"url": self.browser.url})


if __name__ == "__main__":
    unittest.main()
