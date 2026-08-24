# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for complete Car UI runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from config.application_config import (
    ApplicationConfig,
    ApplicationsConfig,
    ApplicationType,
    BrowserConfig,
)
from config.runtime_config import (
    RuntimeConfig,
    InputConfig,
    RadioStackConfig,
    RigctlConfig,
    RotaryEncoderConfig,
    SeesawEncoderConfig,
    RuntimeDisplayConfig,
)
from apps.carUi.runtime.car_ui_runtime_factory import (
    CarUiRuntimeFactoryError,
    build_car_ui_runtime,
)
from apps.carUi.runtime.radio_runtime_registry import RadioRuntimeRegistry
from apps.launchers.google_earth_launcher import GoogleEarthLauncher


@dataclass(frozen=True)
class FakeMode:
    name: str = "WFM"
    bandwidth: int = 180000
    step_hz: int = 100000


@dataclass(frozen=True)
class FakePreset:
    label: str
    frequency_hz: int
    mode: FakeMode


@dataclass(frozen=True)
class FakeRadioConfig:
    label: str
    default_mode: FakeMode
    presets: tuple[FakePreset, ...]
    radio_range: object | None = None


class RadioRuntimeFactoryTest(unittest.TestCase):
    def _config(
        self,
        *,
        backend: str = "rigctl",
        launcher: str | None = "sdrpp",
        enabled: bool = True,
    ) -> RuntimeConfig:
        return RuntimeConfig(
            runtime=RuntimeDisplayConfig(
                remote_display=":9",
                auxiliary_display=":4",
            ),
            rigctl=RigctlConfig(host="127.0.0.1", port=4532),
            input=InputConfig(
                rotary_encoders=RotaryEncoderConfig(
                    devices=(
                        SeesawEncoderConfig(address=0x36),
                        SeesawEncoderConfig(address=0x37),
                        SeesawEncoderConfig(address=0x38),
                    ),
                    volume_index=0,
                )
            ),
            radios=(
                RadioStackConfig(
                    key="fm_radio",
                    config_path=Path("/tmp/fm_radio.json"),
                    backend=backend,
                    launcher=launcher,
                    enabled=enabled,
                ),
            ),
        )

    @staticmethod
    def _applications() -> ApplicationsConfig:
        return ApplicationsConfig(
            browser=BrowserConfig(profile_root=Path("/tmp/openroadcode-browser")),
            apps=(
                ApplicationConfig(
                    key="adsb",
                    type=ApplicationType.ADSB,
                    enabled=False,
                    url="http://127.0.0.1/tar1090",
                ),
                ApplicationConfig(
                    key="weather",
                    type=ApplicationType.BROWSER,
                    enabled=False,
                    url="http://127.0.0.1:8501",
                    profile="weather",
                ),
                ApplicationConfig(
                    key="google_earth",
                    type=ApplicationType.BROWSER,
                    enabled=True,
                    url="https://earth.google.com/web",
                    profile="google-earth",
                    exclusive_group="auxiliary",
                ),
            ),
        )

    @patch("apps.carUi.runtime.car_ui_runtime_factory.SDRResourceManager")
    @patch("apps.carUi.runtime.car_ui_runtime_factory.SDRPPLauncher")
    @patch("apps.carUi.runtime.car_ui_runtime_factory.RigctlRadioBackend")
    @patch("apps.carUi.runtime.car_ui_runtime_factory.RigctlClient")
    @patch("apps.carUi.runtime.car_ui_runtime_factory.RadioController")
    @patch("apps.carUi.runtime.car_ui_runtime_factory.load_radio_config")
    def test_builds_enabled_radio_runtime(
        self,
        load_radio_config,
        radio_controller,
        rigctl_client,
        rigctl_backend,
        sdrpp_launcher,
        resource_manager,
    ) -> None:
        load_radio_config.return_value = FakeRadioConfig(
            label="FM Radio",
            default_mode=FakeMode(),
            presets=(FakePreset("97.1 FM", 97100000, FakeMode()),),
        )

        runtime = build_car_ui_runtime(self._config())

        self.assertEqual(":9", runtime.remote_display)
        self.assertEqual(":4", runtime.auxiliary_display)
        self.assertEqual(3, len(runtime.rotary_encoders.devices))
        self.assertIn("fm_radio", runtime.radios)
        self.assertEqual(1, len(runtime.radios))
        rigctl_client.assert_called_once_with(host="127.0.0.1", port=4532)
        rigctl_backend.assert_called_once()
        radio_controller.assert_called_once()
        sdrpp_launcher.assert_called_once()

    @patch("apps.carUi.runtime.car_ui_runtime_factory.GoogleEarthLauncher")
    @patch("apps.carUi.runtime.car_ui_runtime_factory.BrowserApplicationFactory")
    @patch("apps.carUi.runtime.car_ui_runtime_factory.SDRResourceManager")
    def test_google_earth_uses_specialized_managed_launcher(
        self,
        resource_manager,
        browser_factory_type,
        google_earth_type,
    ) -> None:
        browser = Mock()
        browser_factory = browser_factory_type.return_value
        browser_factory.create_from_config.return_value = browser
        google_earth = google_earth_type.return_value

        runtime = build_car_ui_runtime(
            self._config(enabled=False),
            applications_config=self._applications(),
        )

        google_earth_config = self._applications().app("google_earth")
        browser_factory.create_from_config.assert_called_once_with(google_earth_config)
        google_earth_type.assert_called_once_with(browser=browser)
        self.assertIsNotNone(runtime.app_runtime_manager)
        self.assertIs(
            google_earth,
            runtime.app_runtime_manager.launcher("google_earth"),
        )

    @patch("apps.carUi.runtime.car_ui_runtime_factory.SDRResourceManager")
    def test_disabled_radio_is_not_assembled(self, resource_manager) -> None:
        runtime = build_car_ui_runtime(self._config(enabled=False))
        self.assertEqual(0, len(runtime.radios))

    @patch("apps.carUi.runtime.car_ui_runtime_factory.SDRResourceManager")
    @patch("apps.carUi.runtime.car_ui_runtime_factory.load_radio_config")
    def test_unsupported_backend_is_rejected(
        self,
        load_radio_config,
        resource_manager,
    ) -> None:
        load_radio_config.return_value = FakeRadioConfig(
            label="FM Radio",
            default_mode=FakeMode(),
            presets=(),
        )

        with self.assertRaisesRegex(CarUiRuntimeFactoryError, "Unsupported radio backend"):
            build_car_ui_runtime(self._config(backend="mystery"))

    def test_registry_reports_available_keys(self) -> None:
        registry = RadioRuntimeRegistry({})
        with self.assertRaisesRegex(KeyError, "Available: <none>"):
            registry.get("fm_radio")


if __name__ == "__main__":
    unittest.main()
