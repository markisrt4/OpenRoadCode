"""Explicit UI contracts and stubs for automotive displays."""

from ui.automotive.automotive_if import AutomotiveUiIf, VehicleStatus
from ui.automotive.automotive_ui_stub import AutomotiveUiStub
from ui.automotive.vehicle_ui_if import VehicleUiIf
from ui.automotive.vehicle_ui_stub import VehicleUiStub

__all__ = [
    "AutomotiveUiIf",
    "AutomotiveUiStub",
    "VehicleStatus",
    "VehicleUiIf",
    "VehicleUiStub",
]
