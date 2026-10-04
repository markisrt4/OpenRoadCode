# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapt system audio output to the generic media-volume contract."""

import logging

from common.logging.structured import current_operation, event, operation

from controllers.audio.audio_controller_if import AudioControllerIf
from ui.media import VolumeRequestHandlerIf

LOGGER = logging.getLogger("media.audio")


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
        with operation(current_operation()):
            try:
                self._audio_controller.set_volume_level(level)
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "audio.command_failed",
                    "Media audio volume command failed",
                    action="volume",
                    exception_type=type(error).__name__,
                )
                raise
            event(
                LOGGER,
                logging.DEBUG,
                "audio.command_completed",
                "Media audio volume command completed",
                action="volume",
            )
