"""Explicit UI contracts and stubs for media playback."""

from ui.media.media_ui_if import MediaState, MediaUiIf, PlaybackState
from ui.media.media_ui_stub import MediaUiStub
from ui.media.playback_request_handler_if import PlaybackRequestHandlerIf
from ui.media.playback_request_handler_stub import PlaybackRequestHandlerStub
from ui.media.seek_request_handler_if import SeekRequestHandlerIf
from ui.media.seek_request_handler_stub import SeekRequestHandlerStub
from ui.media.track_request_handler_if import TrackRequestHandlerIf
from ui.media.track_request_handler_stub import TrackRequestHandlerStub
from ui.media.volume_request_handler_if import VolumeRequestHandlerIf
from ui.media.volume_request_handler_stub import VolumeRequestHandlerStub

__all__ = [
    "MediaState",
    "MediaUiIf",
    "MediaUiStub",
    "PlaybackRequestHandlerIf",
    "PlaybackRequestHandlerStub",
    "PlaybackState",
    "SeekRequestHandlerIf",
    "SeekRequestHandlerStub",
    "TrackRequestHandlerIf",
    "TrackRequestHandlerStub",
    "VolumeRequestHandlerIf",
    "VolumeRequestHandlerStub",
]
