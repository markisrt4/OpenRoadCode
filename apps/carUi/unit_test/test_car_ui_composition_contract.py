# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify composition depends only on frontend and screen-factory contracts."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from apps.carUi.car_ui_composition import CarUiComposition
from apps.carUi.screens.car_ui_screen_factory_if import CarUiScreens


class RecordingScreen:
    def __init__(self, key: str) -> None:
        self.key = key
        self.shows = 0

    def show(self) -> None:
        self.shows += 1

    def hide(self) -> None:
        pass

    def handle_ui_action(self, _action) -> bool:
        return False

    def set_vehicle_message(self, _message) -> None:
        pass

    def set_vehicle_error(self, _topic, _error) -> None:
        pass

    def set_attitude_message(self, _message) -> None:
        pass

    def set_imu_message(self, _message) -> None:
        pass

    def set_position_message(self, _message) -> None:
        pass

    def set_motion_message(self, _message) -> None:
        pass

    def set_navigation_error(self, _topic, _error) -> None:
        pass


class FakeScreenFactory:
    def __init__(self) -> None:
        self.screens = {
            key: RecordingScreen(key)
            for key in (
                "aircraft", "weather", "lighting", "fm_radio", "scanner",
                "spotify", "netflix", "youtube", "offroad_dashboard",
                "vehicle_gauges", "turn_by_turn",
            )
        }

    def create_screens(self, _dependencies, _frequency, _dispatch) -> CarUiScreens:
        return CarUiScreens(**self.screens)  # type: ignore[arg-type]


class FakeFrontend:
    empty_value = "--"

    def __init__(self) -> None:
        self.top_bar = Mock()
        self.status_bar = Mock()
        self.volume_panel = Mock()

    def dispatch_ui(self, callback) -> None:
        callback()

    def schedule_ui_callback(self, _delay, _callback):
        return "job"

    def cancel_ui_callback(self, _callback_id) -> None:
        pass

    def handle_ui_action(self, _action) -> None:
        pass

    def show_menu(self, _key) -> None:
        pass

    def show_main_menu(self) -> None:
        pass

    def show_screen(self, _screen_id) -> None:
        pass

    def close(self) -> None:
        pass


class CarUiCompositionContractTest(unittest.TestCase):
    @patch("apps.carUi.car_ui_composition.ZeroMqSubscriber")
    def test_fake_frontend_and_factory_assemble_without_tk(self, subscriber_type) -> None:
        subscriber_type.return_value = Mock()
        frontend = FakeFrontend()
        factory = FakeScreenFactory()
        audio = Mock()
        audio.get_volume_level.return_value = 10
        audio.steps = 20
        audio.is_muted.return_value = False

        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "runtime.toml"
            config_path.write_text(
                "[messaging]\n"
                "publisher_endpoint = \"tcp://127.0.0.1:5556\"\n"
                "subscriber_endpoint = \"tcp://127.0.0.1:5557\"\n"
            )
            dependencies = SimpleNamespace(
                runtime=SimpleNamespace(remote_display=":0", config_path=config_path),
                audio_controller=audio,
                spotify_controller=Mock(),
                lighting_controller=Mock(),
                rotary_encoders=(Mock(),),
                volume_encoder_index=0,
                keyboards=(),
                push_buttons=(),
                push_button_actions=(),
            )

            composition = CarUiComposition(frontend, dependencies, factory)  # type: ignore[arg-type]
            composition.open_route("spotify")

        self.assertEqual(factory.screens["spotify"].shows, 1)
        frontend.volume_panel.set_volume_request_handler.assert_called_once()


if __name__ == "__main__":
    unittest.main()
