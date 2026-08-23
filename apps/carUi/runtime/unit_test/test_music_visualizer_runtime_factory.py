# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for native Car UI music-visualizer composition."""

import os
from unittest.mock import patch

from apps.carUi.runtime.music_visualizer_runtime_factory import (
    create_music_visualizer_runtime,
)
from controllers.audio_analysis.selectable_music_analysis_source import MusicAudioInput


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


@patch("apps.carUi.runtime.music_visualizer_runtime_factory.PipeWireAudioCapture")
def test_external_input_uses_default_source(capture_type):
    runtime = create_music_visualizer_runtime()
    try:
        runtime.analysis_source.select_input(MusicAudioInput.EXTERNAL_INPUT)
        assert [call.kwargs["device"] for call in capture_type.call_args_list] == [
            "@DEFAULT_MONITOR@",
            "@DEFAULT_SOURCE@",
        ]
    finally:
        runtime.close()


@patch("apps.carUi.runtime.music_visualizer_runtime_factory.PipeWireAudioCapture")
def test_external_input_device_can_be_overridden(capture_type):
    with patch.dict(os.environ,{"CARUI_VISUALIZER_INPUT":"external_input","CARUI_VISUALIZER_EXTERNAL_DEVICE":"alsa_input.usb-test"}):
        runtime=create_music_visualizer_runtime()
    try:
        capture_type.assert_called_once_with(device="alsa_input.usb-test")
        assert runtime.analysis_source.input is MusicAudioInput.EXTERNAL_INPUT
    finally:
        runtime.close()
