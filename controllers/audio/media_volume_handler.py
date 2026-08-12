# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt system audio output to the generic media-volume contract."""

from controllers.audio.audio_controller_if import AudioControllerIf
from ui.media import VolumeRequestHandlerIf


class MediaVolumeHandler(VolumeRequestHandlerIf):
    """Apply normalized media volume requests to system audio output."""

    def __init__(self, audio_controller: AudioControllerIf) -> None:
        self._audio_controller = audio_controller

    def request_volume(self, volume_percent: int) -> None:
        """Set system output volume from a normalized percentage.

        @param volume_percent Requested volume from 0 through 100.
        """
        maximum = self._audio_controller.maximum_level
        level = round(max(0, min(100, volume_percent)) * maximum / 100)
        self._audio_controller.set_volume_level(level)
