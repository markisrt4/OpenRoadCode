# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for native Car UI music-visualizer composition."""

import os
from unittest.mock import patch

from apps.carUi.runtime.music_visualizer_runtime_factory import (
    create_music_visualizer_runtime,
)


@patch("apps.carUi.runtime.music_visualizer_runtime_factory.PipeWireAudioCapture")
def test_car_ui_defaults_to_system_audio_capture(capture_type):
    runtime = create_music_visualizer_runtime()
    try:
        capture_type.assert_called_once_with(device="@DEFAULT_MONITOR@")
    finally:
        runtime.close()


@patch("apps.carUi.runtime.music_visualizer_runtime_factory.PipeWireAudioCapture")
def test_car_ui_audio_device_can_be_overridden(capture_type):
    with patch.dict(
        os.environ,
        {"CARUI_VISUALIZER_AUDIO_DEVICE": "@DEFAULT_SOURCE@"},
    ):
        runtime = create_music_visualizer_runtime()
    try:
        capture_type.assert_called_once_with(device="@DEFAULT_SOURCE@")
    finally:
        runtime.close()
