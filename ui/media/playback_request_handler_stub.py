"""Concrete no-op media playback request handler."""

from ui.media.playback_request_handler_if import PlaybackRequestHandlerIf


class PlaybackRequestHandlerStub(PlaybackRequestHandlerIf):
    """Ignore media playback requests."""

    def request_play(self) -> None:
        pass

    def request_pause(self) -> None:
        pass
