# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the radio controller-to-UI adapter."""

import unittest

from apps.carUi.radio.radio_session_controller import RadioSessionController
from apps.carUi.radio.radio_session_config import RadioSessionConfig
from controllers.radio.radio_controller_stub import RadioControllerStub
from controllers.radio.radio_types import RadioPreset
from ui.radio import RadioUiStub, TunedSignal


class RecordingRadioUi(RadioUiStub):
    def __init__(self) -> None:
        self.presets = []
        self.signal: TunedSignal | None = None
        self.receiver_active = False
        self.active_preset = None
        self.handlers = []

    def clear_presets(self) -> None:
        self.presets.clear()

    def add_preset(self, preset) -> None:
        self.presets.append(preset)

    def set_signal(self, signal: TunedSignal | None) -> None:
        self.signal = signal

    def set_receiver_active(self, active: bool) -> None:
        self.receiver_active = active

    def set_active_preset(self, preset_index: int | None) -> None:
        self.active_preset = preset_index

    def set_preset_request_handler(self, handler) -> None:
        self.handlers.append(handler)

    def set_playback_request_handler(self, handler) -> None:
        self.handlers.append(handler)

    def set_station_request_handler(self, handler) -> None:
        self.handlers.append(handler)

    def set_tuning_request_handler(self, handler) -> None:
        self.handlers.append(handler)

    def set_application_request_handler(self, handler) -> None:
        self.handlers.append(handler)

    def set_refresh_request_handler(self, handler) -> None:
        self.handlers.append(handler)


class StubLauncher:
    def toggle(self, remote_display, set_status=None) -> bool:
        return True


class RadioSessionControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        mode = RadioControllerStub.DEFAULT_MODE
        preset = RadioPreset("Test FM", 88_100_000, mode)
        self.radio = RadioControllerStub(presets=(preset,))
        config = RadioSessionConfig(
            key="fm_radio",
            title="FM Radio",
            default_step_hz=mode.step_hz,
        )
        self.session = RadioSessionController(
            radio_controller=self.radio,
            radio_app_launcher=StubLauncher(),  # type: ignore[arg-type]
            session_config=config,
        )
        self.ui = RecordingRadioUi()
        self.session.set_radio_ui(self.ui)

    def test_attach_populates_presets_and_handlers(self) -> None:
        self.assertEqual([preset.label for preset in self.ui.presets], ["Test FM"])
        self.assertEqual(self.ui.handlers, [self.session] * 6)

    def test_play_and_refresh_publish_generic_ui_state(self) -> None:
        self.session.request_play()
        self.session.request_radio_refresh()

        self.assertTrue(self.ui.receiver_active)
        self.assertIsNotNone(self.ui.signal)
        self.assertEqual(self.ui.signal.frequency_hz, 88_100_000)  # type: ignore[union-attr]


if __name__ == "__main__":
    unittest.main()
