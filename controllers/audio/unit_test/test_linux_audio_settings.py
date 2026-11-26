# SPDX-License-Identifier: MIT
"""Exercise the PipeWire and BlueZ audio settings operations."""

from unittest.mock import Mock

import pytest

from controllers.audio.linux_audio_settings import LinuxAudioSettings
from ui.system.audio_settings_if import AudioAction


def test_receivers_exclude_non_audio_devices_and_report_connections():
    settings = LinuxAudioSettings(Mock())
    settings._run = Mock(
        side_effect=[
            "Device 01:02:03:04:05:06 Speaker\nDevice 01:02:03:04:05:07 Mouse",
            "Icon: audio-speakers\nPaired: yes\nConnected: yes",
            "Icon: input-mouse\nPaired: yes",
        ]
    )
    try:
        (receiver,) = settings._receivers()
        assert receiver.name == "Speaker"
        assert receiver.selected and receiver.paired
    finally:
        settings.close()


def test_setting_output_refuses_unavailable_sink():
    settings = LinuxAudioSettings(Mock())
    settings._run = Mock(return_value="[]")
    try:
        with pytest.raises(RuntimeError, match="no longer available"):
            settings._perform(AudioAction.SELECT_OUTPUT, "missing")
        settings._run.assert_called_once_with("pactl", "-f", "json", "list", "sinks")
    finally:
        settings.close()
