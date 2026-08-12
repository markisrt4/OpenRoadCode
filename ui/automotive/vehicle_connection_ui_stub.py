# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op vehicle connection UI implementation."""

from ui.automotive.vehicle_connection_ui_if import (
    VehicleConnectionState,
    VehicleConnectionUiIf,
)


class VehicleConnectionUiStub(VehicleConnectionUiIf):
    """Ignore vehicle connection-state updates."""

    def set_connection_state(
        self,
        state: VehicleConnectionState | None,
    ) -> None:
        pass
