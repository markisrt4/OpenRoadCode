# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Explicit UI contracts and stubs for automotive displays."""

from ui.automotive.diagnostics_request_handler_if import (
    DiagnosticsRequestHandlerIf,
)
from ui.automotive.diagnostics_request_handler_stub import (
    DiagnosticsRequestHandlerStub,
)
from ui.automotive.vehicle_body_ui_if import (
    ExteriorLight,
    SeatPosition,
    VehicleBodyUiIf,
    VehicleOpening,
)
from ui.automotive.vehicle_body_ui_stub import VehicleBodyUiStub
from ui.automotive.vehicle_connection_ui_if import (
    VehicleConnectionState,
    VehicleConnectionUiIf,
)
from ui.automotive.vehicle_connection_ui_stub import VehicleConnectionUiStub
from ui.automotive.vehicle_diagnostics_ui_if import (
    DiagnosticSeverity,
    DiagnosticStatus,
    DiagnosticTroubleCode,
    VehicleDiagnosticsUiIf,
)
from ui.automotive.vehicle_diagnostics_ui_stub import VehicleDiagnosticsUiStub
from ui.automotive.vehicle_tire_ui_if import TirePosition, VehicleTireUiIf
from ui.automotive.vehicle_tire_ui_stub import VehicleTireUiStub
from ui.automotive.vehicle_trip_ui_if import VehicleTripUiIf
from ui.automotive.vehicle_trip_ui_stub import VehicleTripUiStub
from ui.automotive.vehicle_ui_if import Gear, VehicleUiIf
from ui.automotive.vehicle_ui_stub import VehicleUiStub

__all__ = [
    "DiagnosticSeverity",
    "DiagnosticStatus",
    "DiagnosticTroubleCode",
    "DiagnosticsRequestHandlerIf",
    "DiagnosticsRequestHandlerStub",
    "ExteriorLight",
    "Gear",
    "SeatPosition",
    "TirePosition",
    "VehicleBodyUiIf",
    "VehicleBodyUiStub",
    "VehicleConnectionState",
    "VehicleConnectionUiIf",
    "VehicleConnectionUiStub",
    "VehicleDiagnosticsUiIf",
    "VehicleDiagnosticsUiStub",
    "VehicleOpening",
    "VehicleTireUiIf",
    "VehicleTireUiStub",
    "VehicleTripUiIf",
    "VehicleTripUiStub",
    "VehicleUiIf",
    "VehicleUiStub",
]
