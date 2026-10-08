# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for toolkit-independent system volume request handling."""

import unittest
from unittest.mock import Mock

from controllers.audio.system_volume_handler import SystemVolumeHandler


class SystemVolumeHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.audio = Mock()
        self.audio.is_available = True
        self.audio.status_message = None
        self.audio.maximum_level = 20
        self.ui = Mock()
        self.status = Mock()
        self.handler = SystemVolumeHandler(
            audio_controller=self.audio,
            volume_ui=self.ui,
            set_status=self.status,
        )

    def test_refresh_publishes_normalized_volume_and_mute(self) -> None:
        self.audio.get_volume_level.return_value = 8
        self.audio.is_muted.return_value = False

        self.handler.refresh()

        self.ui.set_volume.assert_called_once_with(40.0)
        self.ui.set_muted.assert_called_once_with(False)

    def test_refresh_reports_unavailable_controller_without_backend_calls(self) -> None:
        self.audio.is_available = False
        self.audio.status_message = "No audio backend"

        self.handler.refresh()

        self.ui.set_volume.assert_called_once_with(None)
        self.ui.set_muted.assert_called_once_with(None)
        self.status.assert_called_once_with("No audio backend")
        self.audio.get_volume_level.assert_not_called()

    def test_absolute_volume_is_clamped_and_scaled(self) -> None:
        self.audio.set_volume_level.return_value = 20

        self.handler.request_volume(130.0)

        self.audio.set_volume_level.assert_called_once_with(20)
        self.ui.set_volume.assert_called_once_with(100.0)

    def test_volume_up_publishes_resulting_level(self) -> None:
        self.audio.volume_up.return_value = 11

        self.handler.request_volume_up()

        self.audio.volume_up.assert_called_once_with()
        self.ui.set_volume.assert_called_once_with(55.0)

    def test_volume_down_publishes_resulting_level(self) -> None:
        self.audio.volume_down.return_value = 3

        self.handler.request_volume_down()

        self.audio.volume_down.assert_called_once_with()
        self.ui.set_volume.assert_called_once_with(15.0)

    def test_mute_toggles_only_when_requested_state_differs(self) -> None:
        self.audio.is_muted.return_value = False
        self.audio.toggle_mute.return_value = True

        self.handler.request_mute(True)

        self.audio.toggle_mute.assert_called_once_with()
        self.ui.set_muted.assert_called_once_with(True)

    def test_matching_mute_state_does_not_toggle(self) -> None:
        self.audio.is_muted.return_value = True

        self.handler.request_mute(True)

        self.audio.toggle_mute.assert_not_called()
        self.ui.set_muted.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
