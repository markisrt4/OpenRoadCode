"""Concrete no-op application status UI implementation."""

from ui.system.status_ui_if import StatusMessage, StatusUiIf
from ui.ui_stub import UiStub


class StatusUiStub(UiStub, StatusUiIf):
    """Ignore application status updates."""

    def set_status(self, status: StatusMessage | None) -> None:
        pass
