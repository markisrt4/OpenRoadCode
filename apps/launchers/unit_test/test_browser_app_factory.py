# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
import unittest

from apps.launchers.browser_app_factory import BrowserApplicationFactory
from apps.launchers.external_window_manager import ExternalWindowManager
from config.application_config import (
    ApplicationConfig,
    ApplicationsConfig,
    ApplicationType,
    BrowserConfig,
)


class BrowserApplicationFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.window_manager = ExternalWindowManager()
        self.config = ApplicationsConfig(
            browser=BrowserConfig(profile_root=Path("/tmp/openroadcode-browser")),
            apps=(
                ApplicationConfig(
                    key="weather",
                    type=ApplicationType.BROWSER,
                    url="http://127.0.0.1:8501",
                    profile="weather",
                    exclusive_group="auxiliary",
                ),
                ApplicationConfig(
                    key="web_ui",
                    type=ApplicationType.BROWSER,
                    url="http://127.0.0.1:5000",
                    profile="web-ui",
                ),
                ApplicationConfig(
                    key="adsb",
                    type=ApplicationType.ADSB,
                    url="http://127.0.0.1/tar1090",
                ),
                ApplicationConfig(
                    key="disabled",
                    type=ApplicationType.BROWSER,
                    enabled=False,
                    url="https://example.invalid",
                    profile="disabled",
                ),
            ),
        )
        self.factory = BrowserApplicationFactory(
            self.config,
            window_manager=self.window_manager,
        )

    def test_create_maps_browser_configuration_to_launcher(self) -> None:
        launcher = self.factory.create("weather")

        self.assertEqual("http://127.0.0.1:8501", launcher.url)
        self.assertEqual(
            Path("/tmp/openroadcode-browser/weather"),
            launcher.profile_path,
        )
        self.assertEqual("openroadcode-weather", launcher.window_class)
        self.assertEqual("auxiliary", launcher.exclusive_group)
        self.assertIs(self.window_manager, launcher._window_manager)

    def test_window_class_is_stable_for_underscored_key(self) -> None:
        launcher = self.factory.create("web_ui")

        self.assertEqual("openroadcode-web-ui", launcher.window_class)

    def test_non_browser_application_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not browser"):
            self.factory.create("adsb")

    def test_disabled_browser_application_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.factory.create("disabled")


if __name__ == "__main__":
    unittest.main()
