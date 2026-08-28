# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for weather dashboard launcher configuration and lifecycle."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from apps.launchers.weather_dash_launcher import WeatherDashLauncher


class WeatherDashLauncherTest(unittest.TestCase):
    def test_constructor_configures_weather_streamlit_app(self) -> None:
        browser = Mock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            launcher = WeatherDashLauncher(
                project_root=root,
                port=8765,
                cache_directory=root / "weather-cache",
                refresh_seconds=45,
                browser=browser,
            )

            self.assertEqual(root / "apps" / "weatherDash" / "main.py", launcher.app_path)
            self.assertEqual(8765, launcher.port)
            self.assertEqual(browser, launcher.browser)
            self.assertEqual(
                str(root / "weather-cache"),
                launcher.environment["OPENROAD_WEATHER_CACHE_DIRECTORY"],
            )
            self.assertEqual(
                "45", launcher.environment["OPENROAD_WEATHER_REFRESH_SECONDS"]
            )

    @patch("apps.launchers.weather_dash_launcher.StreamlitLauncher.launch")
    def test_launch_reports_status_and_delegates(self, launch: Mock) -> None:
        launcher = WeatherDashLauncher(browser=Mock())
        status = Mock()

        launcher.launch(":1", status)

        status.assert_any_call("Launching weather dashboard...")
        launch.assert_called_once_with(":1", status)


if __name__ == "__main__":
    unittest.main()
