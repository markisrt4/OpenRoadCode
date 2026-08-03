"""Concrete no-op media track request handler."""

from ui.media.track_request_handler_if import TrackRequestHandlerIf


class TrackRequestHandlerStub(TrackRequestHandlerIf):
    """Ignore media track-navigation requests."""

    def request_previous_track(self) -> None:
        pass

    def request_next_track(self) -> None:
        pass
