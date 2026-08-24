# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from apps.launchers.app_runtime_manager import AppRuntimeManager
from config.application_config import ApplicationConfig, ApplicationsConfig, ApplicationType, BrowserConfig, StartupPolicy


class FakeLauncher:
    def __init__(self) -> None:
        self.launches = 0
        self.stops = 0
        self.prepares = 0
        self.running = False

    def launch(self, remote_display: str, set_status=None) -> None:
        self.launches += 1
        self.running = True

    def stop(self, remote_display: str, set_status=None) -> None:
        self.stops += 1
        self.running = False

    def toggle(self, remote_display: str, set_status=None) -> bool:
        self.running = not self.running
        return self.running

    def is_running(self) -> bool:
        return self.running

    def prepare(self) -> None:
        self.prepares += 1
        self.running = True


class AppRuntimeManagerTest(unittest.TestCase):
    def _config(self, policy: StartupPolicy) -> ApplicationsConfig:
        return ApplicationsConfig(
            browser=BrowserConfig(),
            apps=(ApplicationConfig(key="weather", type=ApplicationType.BROWSER, startup=policy, url="http://127.0.0.1:8501", profile="weather"),),
        )

    def test_lazy_app_is_not_started_in_background(self) -> None:
        launcher = FakeLauncher()
        manager = AppRuntimeManager(self._config(StartupPolicy.LAZY), remote_display=":2")
        manager.register("weather", launcher)
        manager._start_background_apps(None)
        self.assertEqual(0, launcher.launches)
        self.assertEqual(0, launcher.prepares)

    def test_preload_app_prepares_without_presenting(self) -> None:
        launcher = FakeLauncher()
        manager = AppRuntimeManager(self._config(StartupPolicy.PRELOAD), remote_display=":2")
        manager.register("weather", launcher)
        manager._start_background_apps(None)
        self.assertEqual(1, launcher.prepares)
        self.assertEqual(0, launcher.launches)

    def test_persistent_app_launches_in_background(self) -> None:
        launcher = FakeLauncher()
        manager = AppRuntimeManager(self._config(StartupPolicy.PERSISTENT), remote_display=":2")
        manager.register("weather", launcher)
        manager._start_background_apps(None)
        self.assertEqual(1, launcher.launches)

    def test_launch_presents_registered_app(self) -> None:
        launcher = FakeLauncher()
        manager = AppRuntimeManager(self._config(StartupPolicy.LAZY), remote_display=":2")
        manager.register("weather", launcher)
        manager.launch("weather")
        self.assertEqual(1, launcher.launches)

    def test_stop_all_stops_preloaded_app(self) -> None:
        launcher = FakeLauncher()
        manager = AppRuntimeManager(self._config(StartupPolicy.PRELOAD), remote_display=":2")
        manager.register("weather", launcher)
        manager._start_background_apps(None)
        manager.stop_all()
        self.assertEqual(1, launcher.stops)

    def test_duplicate_registration_is_rejected(self) -> None:
        launcher = FakeLauncher()
        manager = AppRuntimeManager(self._config(StartupPolicy.LAZY), remote_display=":2")
        manager.register("weather", launcher)
        with self.assertRaisesRegex(ValueError, "already registered"):
            manager.register("weather", launcher)


if __name__ == "__main__":
    unittest.main()
