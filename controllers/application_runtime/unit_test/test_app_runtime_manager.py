# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import unittest

from controllers.application_runtime import AppRuntimeManager
from config.application_config import (
    ApplicationConfig, ApplicationsConfig, ApplicationType, BrowserConfig,
    PresentationTargetConfig, PresentationTargetType, StartupPolicy,
)


class FakeLauncher:
    def __init__(self) -> None:
        self.launches = 0; self.stops = 0; self.prepares = 0; self.running = False
        self.launch_displays: list[str] = []; self.stop_displays: list[str] = []; self.prepare_displays: list[str] = []

    def launch(self, remote_display: str, set_status=None) -> None:
        self.launches += 1; self.launch_displays.append(remote_display); self.running = True

    def stop(self, remote_display: str, set_status=None) -> None:
        self.stops += 1; self.stop_displays.append(remote_display); self.running = False

    def toggle(self, remote_display: str, set_status=None) -> bool:
        self.running = not self.running; return self.running

    def is_running(self) -> bool:
        return self.running

    def prepare(self, remote_display: str, set_status=None) -> None:
        self.prepares += 1; self.prepare_displays.append(remote_display); self.running = True


class FakeWindowedLauncher:
    def __init__(self) -> None:
        self.launches = 0; self.shows = 0; self.hides = 0; self.stops = 0; self.running = False; self.visible = False

    def launch(self, remote_display: str, set_status=None) -> None:
        self.launches += 1; self.running = True; self.visible = True

    def show(self, remote_display: str, set_status=None) -> bool:
        self.shows += 1
        if not self.running: return False
        self.visible = True; return True

    def hide(self, remote_display: str, set_status=None) -> bool:
        self.hides += 1
        if not self.running: return False
        self.visible = False; return True

    def stop(self, remote_display: str, set_status=None) -> None:
        self.stops += 1; self.running = False; self.visible = False

    def toggle(self, remote_display: str, set_status=None) -> bool:
        self.visible = not self.visible; return self.visible

    def is_running(self) -> bool:
        return self.running


class FakeBrowserDashboardLauncher(FakeLauncher):
    def __init__(self) -> None:
        super().__init__(); self.browser_closes = 0

    def close_browser(self, remote_display: str, set_status=None) -> None:
        self.browser_closes += 1


class NonPreloadableLauncher:
    def __init__(self) -> None:
        self.launches = 0; self.stops = 0; self.running = False

    def launch(self, remote_display: str, set_status=None) -> None:
        self.launches += 1; self.running = True

    def stop(self, remote_display: str, set_status=None) -> None:
        self.stops += 1; self.running = False

    def toggle(self, remote_display: str, set_status=None) -> bool:
        self.running = not self.running; return self.running

    def is_running(self) -> bool:
        return self.running


class AppRuntimeManagerTest(unittest.TestCase):
    def _config(self, policy: StartupPolicy) -> ApplicationsConfig:
        return ApplicationsConfig(browser=BrowserConfig(), apps=(ApplicationConfig(key="weather", type=ApplicationType.BROWSER, startup=policy, url="http://127.0.0.1:8501", profile="weather"),))

    @staticmethod
    def _target_config(*, app_target: str | None = None) -> ApplicationsConfig:
        return ApplicationsConfig(browser=BrowserConfig(), apps=(ApplicationConfig(key="earth", type=ApplicationType.BROWSER, url="http://earth", profile="earth", target=app_target),), presentation_targets=(PresentationTargetConfig(key="primary", type=PresentationTargetType.X11, display=":0"), PresentationTargetConfig(key="auxiliary", type=PresentationTargetType.X11, display=":2")), default_target="primary")

    def test_default_presentation_target_routes_to_primary_display(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._target_config(), remote_display=":99"); manager.register("earth", launcher); manager.show("earth"); self.assertEqual([":0"], launcher.launch_displays)

    def test_application_target_override_routes_to_auxiliary_display(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._target_config(app_target="auxiliary"), remote_display=":99"); manager.register("earth", launcher); manager.show("earth"); self.assertEqual([":2"], launcher.launch_displays)

    def test_restart_uses_same_configured_target_for_stop_and_launch(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._target_config(app_target="auxiliary"), remote_display=":99"); manager.register("earth", launcher); launcher.running = True; manager.restart("earth"); self.assertEqual([":2"], launcher.stop_displays); self.assertEqual([":2"], launcher.launch_displays)

    def test_lazy_app_is_not_started_in_background(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.LAZY), remote_display=":2"); manager.register("weather", launcher); manager._start_background_apps(None); self.assertEqual(0, launcher.launches); self.assertEqual(0, launcher.prepares)

    def test_preload_app_prepares_without_presenting(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.PRELOAD), remote_display=":2"); manager.register("weather", launcher); manager._start_background_apps(None); self.assertEqual(1, launcher.prepares); self.assertEqual([":2"], launcher.prepare_displays); self.assertEqual(0, launcher.launches); self.assertFalse(manager.is_visible("weather"))

    def test_generic_window_preload_launches_then_hides(self) -> None:
        launcher = FakeWindowedLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.PRELOAD), remote_display=":2"); manager.register("weather", launcher); manager._start_background_apps(None); self.assertEqual(1, launcher.launches); self.assertEqual(1, launcher.hides); self.assertTrue(manager.is_running("weather")); self.assertFalse(manager.is_visible("weather"))

    def test_preloaded_window_show_restores_without_second_launch(self) -> None:
        launcher = FakeWindowedLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.PRELOAD), remote_display=":2"); manager.register("weather", launcher); manager._start_background_apps(None); manager.show("weather"); self.assertEqual(1, launcher.launches); self.assertEqual(1, launcher.shows); self.assertTrue(manager.is_running("weather")); self.assertTrue(manager.is_visible("weather"))

    def test_preload_without_prepare_falls_back_to_launch(self) -> None:
        launcher = NonPreloadableLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.PRELOAD), remote_display=":2"); manager.register("weather", launcher); manager._start_background_apps(None); self.assertEqual(1, launcher.launches)

    def test_persistent_app_launches_in_background(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.PERSISTENT), remote_display=":2"); manager.register("weather", launcher); manager._start_background_apps(None); self.assertEqual(1, launcher.launches)

    def test_persistent_non_browser_close_keeps_process_running(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.PERSISTENT), remote_display=":2"); manager.register("weather", launcher); launcher.running = True; manager.close("weather"); self.assertEqual(0, launcher.stops); self.assertTrue(launcher.running)

    def test_preloaded_browser_close_only_closes_browser_view(self) -> None:
        launcher = FakeBrowserDashboardLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.PRELOAD), remote_display=":2"); manager.register("weather", launcher); launcher.running = True; manager.close("weather"); self.assertEqual(1, launcher.browser_closes); self.assertEqual(0, launcher.stops); self.assertTrue(launcher.running)

    def test_launch_presents_registered_app(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.LAZY), remote_display=":2"); manager.register("weather", launcher); manager.launch("weather"); self.assertEqual(1, launcher.launches)

    def test_launch_closes_running_peer_in_same_exclusive_group(self) -> None:
        config = ApplicationsConfig(browser=BrowserConfig(), apps=(ApplicationConfig(key="weather", type=ApplicationType.BROWSER, url="http://weather", profile="weather", exclusive_group="auxiliary"), ApplicationConfig(key="web_ui", type=ApplicationType.BROWSER, url="http://web-ui", profile="web-ui", exclusive_group="auxiliary"))); weather = FakeLauncher(); web_ui = FakeLauncher(); manager = AppRuntimeManager(config, remote_display=":2"); manager.register("weather", weather); manager.register("web_ui", web_ui); weather.running = True; manager.launch("web_ui"); self.assertEqual(1, weather.stops); self.assertEqual(1, web_ui.launches)

    def test_exclusive_handoff_preserves_preloaded_browser_backend(self) -> None:
        config = ApplicationsConfig(browser=BrowserConfig(), apps=(ApplicationConfig(key="weather", type=ApplicationType.BROWSER, startup=StartupPolicy.PRELOAD, url="http://weather", profile="weather", exclusive_group="auxiliary"), ApplicationConfig(key="web_ui", type=ApplicationType.BROWSER, url="http://web-ui", profile="web-ui", exclusive_group="auxiliary"))); weather = FakeBrowserDashboardLauncher(); web_ui = FakeLauncher(); manager = AppRuntimeManager(config, remote_display=":2"); manager.register("weather", weather); manager.register("web_ui", web_ui); weather.running = True; manager.launch("web_ui"); self.assertEqual(1, weather.browser_closes); self.assertEqual(0, weather.stops); self.assertEqual(1, web_ui.launches)

    def test_launch_does_not_close_app_in_different_exclusive_group(self) -> None:
        config = ApplicationsConfig(browser=BrowserConfig(), apps=(ApplicationConfig(key="weather", type=ApplicationType.BROWSER, url="http://weather", profile="weather", exclusive_group="auxiliary"), ApplicationConfig(key="web_ui", type=ApplicationType.BROWSER, url="http://web-ui", profile="web-ui", exclusive_group="primary"))); weather = FakeLauncher(); web_ui = FakeLauncher(); manager = AppRuntimeManager(config, remote_display=":2"); manager.register("weather", weather); manager.register("web_ui", web_ui); weather.running = True; manager.launch("web_ui"); self.assertEqual(0, weather.stops); self.assertEqual(1, web_ui.launches)

    def test_stop_all_stops_preloaded_app(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.PRELOAD), remote_display=":2"); manager.register("weather", launcher); manager._start_background_apps(None); manager.stop_all(); self.assertEqual(1, launcher.stops)

    def test_duplicate_registration_is_rejected(self) -> None:
        launcher = FakeLauncher(); manager = AppRuntimeManager(self._config(StartupPolicy.LAZY), remote_display=":2"); manager.register("weather", launcher)
        with self.assertRaisesRegex(ValueError, "already registered"): manager.register("weather", launcher)


if __name__ == "__main__":
    unittest.main()
