"""Concrete no-op vehicle connection UI implementation."""

from ui.automotive.vehicle_connection_ui_if import (
    VehicleConnectionState,
    VehicleConnectionUiIf,
)
from ui.ui_stub import UiStub


class VehicleConnectionUiStub(UiStub, VehicleConnectionUiIf):
    """Ignore vehicle connection-state updates."""

    def set_connection_state(
        self,
        state: VehicleConnectionState | None,
    ) -> None:
        pass
