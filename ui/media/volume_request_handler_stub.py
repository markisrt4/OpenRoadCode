"""Concrete no-op media volume request handler."""

from ui.media.volume_request_handler_if import VolumeRequestHandlerIf


class VolumeRequestHandlerStub(VolumeRequestHandlerIf):
    """Ignore media volume requests."""

    def request_volume(self, volume_percent: int) -> None:
        pass
