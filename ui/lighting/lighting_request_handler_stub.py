"""Concrete no-op lighting request handler."""

from ui.lighting.lighting_request_handler_if import LightingRequestHandlerIf
from ui.lighting.lighting_ui_if import LightingColor


class LightingRequestHandlerStub(LightingRequestHandlerIf):
    """Ignore semantic lighting requests."""

    def request_power(self, enabled: bool) -> None:
        pass

    def request_color(self, color: LightingColor) -> None:
        pass

    def request_brightness(self, percent: int) -> None:
        pass

    def request_pattern(self, pattern_index: int) -> None:
        pass

    def request_music_mode(self, mode_index: int) -> None:
        pass
