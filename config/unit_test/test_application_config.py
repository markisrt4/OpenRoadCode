# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from config.application_config import (
    ApplicationConfigError,
    ApplicationsConfigParser,
    ApplicationType,
    BrowserConfig,
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
        self.assertEqual(config.browser.profile_root, Path("~/openroad-browser").expanduser())
        weather = config.app("weather")
        self.assertEqual(weather.type, ApplicationType.BROWSER)
        self.assertEqual(weather.startup, StartupPolicy.PRELOAD)
        self.assertEqual(weather.exclusive_group, "auxiliary")
        self.assertEqual(config.preload_apps(), (weather,))
        self.assertFalse(config.app("sdrpp").enabled)

    def test_browser_profile_root_defaults_to_xdg_data_home(self) -> None:
        with patch.dict(os.environ, {"XDG_DATA_HOME": "/mnt/orc-data"}):
            config = self._load("[apps]\n")
            direct = BrowserConfig()
        expected = Path("/mnt/orc-data/openroadcode/browser")
        self.assertEqual(config.browser.profile_root, expected)
        self.assertEqual(direct.profile_root, expected)

    def test_browser_profile_default_follows_environment_changes(self) -> None:
        with patch.dict(os.environ, {"XDG_DATA_HOME": "/mnt/first"}):
            first = self._load("[apps]\n")
        with patch.dict(os.environ, {"XDG_DATA_HOME": "/mnt/second"}):
            second = self._load("[apps]\n")
        self.assertEqual(first.browser.profile_root, Path("/mnt/first/openroadcode/browser"))
        self.assertEqual(second.browser.profile_root, Path("/mnt/second/openroadcode/browser"))

    def test_explicit_browser_profile_overrides_xdg_default(self) -> None:
        with patch.dict(os.environ, {"XDG_DATA_HOME": "/mnt/orc-data"}):
            config = self._load('[browser]\nprofile_root = "~/custom-browser"\n')
        self.assertEqual(config.browser.profile_root, Path("~/custom-browser").expanduser())

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
            self._load('[apps.weather]\ntype = "browser"\nprofile = "weather"\n')

    def test_browser_application_requires_profile(self) -> None:
        with self.assertRaisesRegex(ApplicationConfigError, "profile is required"):
            self._load('[apps.weather]\ntype = "browser"\nurl = "http://127.0.0.1:8501"\n')

    def test_rejects_unknown_startup_policy(self) -> None:
        with self.assertRaisesRegex(ApplicationConfigError, "lazy, preload, persistent"):
            self._load('[apps.sdrpp]\ntype = "native"\nstartup = "whenever"\n')

    def test_rejects_unknown_application_type(self) -> None:
        with self.assertRaisesRegex(ApplicationConfigError, "browser, adsb, native"):
            self._load('[apps.mystery]\ntype = "magic"\n')

    def test_unknown_application_raises_key_error(self) -> None:
        config = self._load("[apps]\n")
        with self.assertRaises(KeyError):
            config.app("missing")


if __name__ == "__main__":
    unittest.main()
