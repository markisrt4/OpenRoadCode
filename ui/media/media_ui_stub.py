# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op media UI implementation."""

from ui.media.media_ui_if import MediaState, MediaUiIf
from ui.media.playback_request_handler_if import PlaybackRequestHandlerIf
from ui.media.seek_request_handler_if import SeekRequestHandlerIf
from ui.media.track_request_handler_if import TrackRequestHandlerIf
from ui.media.volume_request_handler_if import VolumeRequestHandlerIf


class MediaUiStub(MediaUiIf):
    """Ignore media display updates and callback registration."""

    def set_media_state(self, state: MediaState | None) -> None:
        pass

    def set_playback_request_handler(
        self,
        handler: PlaybackRequestHandlerIf | None,
    ) -> None:
        pass

    def set_track_request_handler(
        self,
        handler: TrackRequestHandlerIf | None,
    ) -> None:
        pass

    def set_seek_request_handler(
        self,
        handler: SeekRequestHandlerIf | None,
    ) -> None:
        pass

    def set_volume_request_handler(
        self,
        handler: VolumeRequestHandlerIf | None,
    ) -> None:
        pass
