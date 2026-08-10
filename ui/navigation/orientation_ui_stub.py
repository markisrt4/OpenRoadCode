"""Concrete no-op orientation UI implementation."""

from ui.navigation.orientation_ui_if import HeadingReference, OrientationUiIf


class OrientationUiStub(OrientationUiIf):
    """Ignore orientation display updates."""

    def set_heading(
        self,
        heading_rad: float | None,
        reference: HeadingReference = HeadingReference.TRUE_NORTH,
    ) -> None:
        pass

    def set_pitch(self, pitch_rad: float | None) -> None:
        pass

    def set_roll(self, roll_rad: float | None) -> None:
        pass
