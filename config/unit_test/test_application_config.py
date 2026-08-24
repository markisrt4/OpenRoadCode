# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from config.application_config import (
    ApplicationConfigError,
    ApplicationsConfigParser,
    ApplicationType,
    StartupPolicy,
)


class ApplicationsConfigParserTest(unittest.TestCase):
    def _load(self, text: str):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "applications.toml"
        path.write_text(text, encoding="utf-8")
        return ApplicationsConfigParser(path).load()

    def test_parses_browser_and_application_policies(self) -> None:
        config = self._load(
            """
[browser]
profile_root = "~/openroad-browser"

[apps.weather]
type = "browser"
url = "http://127.0.0.1:8501"
profile = "weather"
startup = "preload"
exclusive_group = "auxiliary"

[apps.sdrpp]
type = "native"
enabled = false
"""
        )

        self.assertEqual(
            config.browser.profile_root,
            Path("~/openroad-browser").expanduser(),
        )
        weather = config.app("weather")
        self.assertEqual(weather.type, ApplicationType.BROWSER)
        self.assertEqual(weather.startup, StartupPolicy.PRELOAD)
        self.assertEqual(weather.exclusive_group, "auxiliary")
        self.assertEqual(config.preload_apps(), (weather,))
        self.assertFalse(config.app("sdrpp").enabled)

    def test_defaults_startup_to_lazy_and_enabled_to_true(self) -> None:
        config = self._load(
            """
[apps.web_ui]
type = "browser"
url = "http://127.0.0.1:5000"
profile = "web-ui"
"""
        )

        app = config.app("web_ui")
        self.assertTrue(app.enabled)
        self.assertEqual(app.startup, StartupPolicy.LAZY)

    def test_browser_application_requires_url(self) -> None:
        with self.assertRaisesRegex(ApplicationConfigError, "url is required"):
            self._load(
                """
[apps.weather]
type = "browser"
profile = "weather"
"""
            )

    def test_browser_application_requires_profile(self) -> None:
        with self.assertRaisesRegex(ApplicationConfigError, "profile is required"):
            self._load(
                """
[apps.weather]
type = "browser"
url = "http://127.0.0.1:8501"
"""
            )

    def test_rejects_unknown_startup_policy(self) -> None:
        with self.assertRaisesRegex(ApplicationConfigError, "lazy, preload, persistent"):
            self._load(
                """
[apps.sdrpp]
type = "native"
startup = "whenever"
"""
            )

    def test_rejects_unknown_application_type(self) -> None:
        with self.assertRaisesRegex(ApplicationConfigError, "browser, adsb, native"):
            self._load(
                """
[apps.mystery]
type = "magic"
"""
            )

    def test_unknown_application_raises_key_error(self) -> None:
        config = self._load("[apps]\n")
        with self.assertRaises(KeyError):
            config.app("missing")


if __name__ == "__main__":
    unittest.main()
