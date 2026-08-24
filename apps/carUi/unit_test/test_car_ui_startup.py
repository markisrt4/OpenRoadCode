# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Car UI startup environment policy."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from apps.carUi.car_ui_startup import (
    STARTUP_ITEMS,
    _env_bool,
    _env_int,
    build_car_ui_dependencies,
    car_ui_splash_enabled,
    resolve_media_display,
)
from config.runtime_target import RuntimeTarget


class CarUiStartupTest(unittest.TestCase):
    def test_linux_media_uses_active_desktop_display(self) -> None:
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            self.assertEqual(
                ":0",
                resolve_media_display(RuntimeTarget.LINUX_DEV, ":2"),
            )

    def test_pi_media_uses_configured_vehicle_display(self) -> None:
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            self.assertEqual(
                ":2",
                resolve_media_display(RuntimeTarget.RPI5, ":2"),
            )

    def test_media_display_override_takes_precedence(self) -> None:
        with patch.dict(
            os.environ, {"DISPLAY": ":0", "CARUI_MEDIA_DISPLAY": ":2"},
            clear=True,
        ):
            self.assertEqual(
                ":2",
                resolve_media_display(
                    RuntimeTarget.LINUX_DEV, ":9", ":1"
                ),
            )

    def test_toml_media_display_precedes_target_default(self) -> None:
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
            self.assertEqual(
                ":2",
                resolve_media_display(
                    RuntimeTarget.LINUX_DEV, ":9", ":2"
                ),
            )

    def test_startup_items_have_unique_keys(self) -> None:
        keys = [item.key for item in STARTUP_ITEMS]

        self.assertEqual(len(keys), len(set(keys)))

    def test_splash_is_enabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(car_ui_splash_enabled())

    def test_false_environment_spellings_disable_splash(self) -> None:
        for value in ("0", "false", "no", "off"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"CARUI_SPLASH": value}):
                    self.assertFalse(car_ui_splash_enabled())

    def test_invalid_integer_uses_default(self) -> None:
        with patch.dict(os.environ, {"TEST_STARTUP_INT": "invalid"}):
            self.assertEqual(_env_int("TEST_STARTUP_INT", 42), 42)

    def test_boolean_helper_uses_requested_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_env_bool("MISSING_STARTUP_BOOL", False))

    @patch(
        "apps.carUi.car_ui_startup.create_spotify_controller",
        side_effect=RuntimeError("spotify failed"),
    )
    @patch("apps.carUi.car_ui_startup.create_audio_controller")
    @patch("apps.carUi.car_ui_startup.create_input_device_runtime")
    @patch("apps.carUi.car_ui_startup.create_rotary_encoder_runtime")
    @patch("apps.carUi.car_ui_startup.create_car_ui_runtime")
    def test_partial_initialization_releases_created_resources(
        self,
        create_runtime,
        create_encoders,
        create_input_devices,
        _create_audio,
        _create_spotify,
    ) -> None:
        events: list[str] = []
        runtime = SimpleNamespace(
            rotary_encoders=object(),
            audio=object(),
            media_display=None,
            input_config=object(),
            start_background_apps=lambda: events.append("background"),
            close=lambda: events.append("runtime"),
        )
        encoder = SimpleNamespace(stop=lambda: events.append("encoder"))
        create_runtime.return_value = runtime
        create_encoders.return_value = SimpleNamespace(
            encoders=(encoder,), volume_index=0
        )
        create_input_devices.return_value = SimpleNamespace(
            keyboards=(),
            push_buttons=(),
            push_button_actions=(),
        )

        with self.assertRaisesRegex(RuntimeError, "spotify failed"):
            build_car_ui_dependencies(lambda *_args: None)

        self.assertEqual(events, ["background", "encoder", "runtime"])


if __name__ == "__main__":
    unittest.main()
