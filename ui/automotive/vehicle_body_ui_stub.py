"""Concrete no-op vehicle body UI implementation."""

from ui.automotive.vehicle_body_ui_if import (
    ExteriorLight,
    SeatPosition,
    VehicleBodyUiIf,
    VehicleOpening,
)


class VehicleBodyUiStub(VehicleBodyUiIf):
    """Ignore vehicle body and occupant updates."""

    def set_opening_state(
        self,
        opening: VehicleOpening,
        is_open: bool | None,
    ) -> None:
        pass

    def set_seat_belt_state(
        self,
        seat: SeatPosition,
        fastened: bool | None,
    ) -> None:
        pass

    def set_exterior_light_state(
        self,
        light: ExteriorLight,
        active: bool | None,
    ) -> None:
        pass

    def set_parking_brake(self, applied: bool | None) -> None:
        pass
