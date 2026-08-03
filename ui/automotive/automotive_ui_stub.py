"""Concrete no-op automotive status UI implementation."""

from ui.automotive.automotive_if import AutomotiveUiIf, VehicleStatus
from ui.ui_stub import UiStub


class AutomotiveUiStub(UiStub, AutomotiveUiIf):
    """Ignore high-level vehicle status updates."""

    def set_vehicle_status(self, status: VehicleStatus) -> None:
        pass
