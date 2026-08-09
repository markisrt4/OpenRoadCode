"""Concrete no-op radio refresh request handler."""

from ui.radio.radio_refresh_request_handler_if import RadioRefreshRequestHandlerIf


class RadioRefreshRequestHandlerStub(RadioRefreshRequestHandlerIf):
    """Ignore requests to refresh radio state."""

    def request_radio_refresh(self) -> None:
        pass
