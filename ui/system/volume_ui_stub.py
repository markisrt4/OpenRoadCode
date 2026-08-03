"""Concrete no-op system volume UI implementation."""

from ui.system.volume_request_handler_if import VolumeRequestHandlerIf
from ui.system.volume_ui_if import VolumeUiIf
from ui.ui_stub import UiStub


class VolumeUiStub(UiStub, VolumeUiIf):
    """Ignore system volume updates and callback registration."""

    def set_volume(self, volume_percent: float | None) -> None:
        pass

    def set_muted(self, muted: bool | None) -> None:
        pass

    def set_volume_request_handler(
        self,
        handler: VolumeRequestHandlerIf | None,
    ) -> None:
        pass
