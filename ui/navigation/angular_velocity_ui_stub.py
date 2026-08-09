"""Concrete no-op angular-velocity UI implementation."""

from ui.navigation.angular_velocity_ui_if import AngularVelocityUiIf


class AngularVelocityUiStub(AngularVelocityUiIf):
    """Ignore angular-velocity display updates."""

    def set_angular_velocity_x(self, angular_velocity_x_rad_s: float | None) -> None:
        pass

    def set_angular_velocity_y(self, angular_velocity_y_rad_s: float | None) -> None:
        pass

    def set_angular_velocity_z(self, angular_velocity_z_rad_s: float | None) -> None:
        pass
