# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from controllers.navigation.google_earth_map_presentation import GoogleEarthMapPresentation


class GoogleEarthMapPresentationTest(unittest.TestCase):
    @patch("controllers.navigation.google_earth_map_presentation.GoogleEarthLauncher")
    def test_focus_updates_location_and_restarts_managed_app(self, launcher_type) -> None:
        launcher = Mock()
        manager = Mock()
        manager.launcher.return_value = launcher
        presentation = GoogleEarthMapPresentation(manager)

        presentation.focus_location(42.8028, -83.0127)

        manager.launcher.assert_called_once_with("google_earth", launcher_type)
        launcher.set_location.assert_called_once_with(42.8028, -83.0127)
        manager.restart.assert_called_once_with("google_earth")

    @patch("controllers.navigation.google_earth_map_presentation.GoogleEarthLauncher")
    def test_altitude_is_currently_ignored(self, launcher_type) -> None:
        launcher = Mock()
        manager = Mock()
        manager.launcher.return_value = launcher
        presentation = GoogleEarthMapPresentation(manager)

        presentation.focus_location(42.8028, -83.0127, altitude_m=250.0)

        launcher.set_location.assert_called_once_with(42.8028, -83.0127)
        manager.restart.assert_called_once_with("google_earth")


if __name__ == "__main__":
    unittest.main()
