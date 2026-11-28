# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for toolkit-independent system volume request handling."""

import unittest
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from controllers.audio.system_volume_handler import VOLUME_CACHE_KEY, SystemVolumeHandler
from controllers.cache import PersistentCache


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

    def test_rotation_persists_level_and_new_handler_restores_it_at_startup(self) -> None:
        with TemporaryDirectory() as directory:
            self.audio.volume_down.return_value = 7
            first = SystemVolumeHandler(
                audio_controller=self.audio, volume_ui=self.ui, cache=PersistentCache(directory)
            )
            first.request_volume_down()

            self.audio.maximum_level = 100
            self.audio.set_volume_level.return_value = 35
            self.audio.is_muted.return_value = True
            restored_ui = Mock()
            second = SystemVolumeHandler(
                audio_controller=self.audio, volume_ui=restored_ui, cache=PersistentCache(directory)
            )
            second.refresh(restore_cached=True)

        self.audio.set_volume_level.assert_called_once_with(35)
        self.audio.toggle_mute.assert_not_called()
        restored_ui.set_volume.assert_called_once_with(35.0)
        restored_ui.set_muted.assert_called_once_with(True)

    def test_failed_restore_reads_the_current_level_and_keeps_saved_value(self) -> None:
        cache = Mock()
        cache.get.return_value = b"0"
        self.audio.set_volume_level.side_effect = OSError("offline")
        self.audio.get_volume_level.return_value = 8
        handler = SystemVolumeHandler(audio_controller=self.audio, volume_ui=self.ui, cache=cache)

        handler.refresh(restore_cached=True)

        self.audio.set_volume_level.assert_called_once_with(0)
        self.ui.set_volume.assert_called_once_with(40.0)
        cache.put.assert_not_called()

    def test_invalid_saved_volume_leaves_the_current_level_in_place(self) -> None:
        cache = Mock()
        cache.get.return_value = b"nan"
        self.audio.get_volume_level.return_value = 8
        handler = SystemVolumeHandler(audio_controller=self.audio, volume_ui=self.ui, cache=cache)

        handler.refresh(restore_cached=True)

        cache.get.assert_called_once_with(VOLUME_CACHE_KEY)
        self.audio.set_volume_level.assert_not_called()
        self.ui.set_volume.assert_called_once_with(40.0)


if __name__ == "__main__":
    unittest.main()
