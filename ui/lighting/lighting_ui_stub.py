"""Concrete no-op lighting UI implementation."""

from ui.lighting.lighting_request_handler_if import LightingRequestHandlerIf
from ui.lighting.lighting_ui_if import LightingState, LightingUiIf


class LightingUiStub(LightingUiIf):
    """Ignore lighting state and callback registration."""

    def set_lighting_state(self, state: LightingState | None) -> None:
        pass

    def set_lighting_request_handler(
        self,
        handler: LightingRequestHandlerIf | None,
    ) -> None:
        pass
