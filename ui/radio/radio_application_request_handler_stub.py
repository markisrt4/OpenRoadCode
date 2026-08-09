"""Concrete no-op companion-radio-application request handler."""

from ui.radio.radio_application_request_handler_if import (
    RadioApplicationRequestHandlerIf,
)


class RadioApplicationRequestHandlerStub(RadioApplicationRequestHandlerIf):
    """Ignore companion radio application requests."""

    def request_toggle_radio_application(self) -> None:
        pass
