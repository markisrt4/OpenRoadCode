# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Audio capture backends for analysis pipelines."""

from .audio_capture_if import AudioCaptureIf, AudioSamplesCallback
from .android_playback_audio_capture import AndroidPlaybackAudioCapture
from .pipewire_audio_capture import PipewireAudioCapture

__all__ = ["AudioCaptureIf", "AudioSamplesCallback", "AndroidPlaybackAudioCapture", "PipewireAudioCapture"]
