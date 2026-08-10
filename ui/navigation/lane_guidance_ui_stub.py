"""Concrete no-op lane-guidance UI implementation."""

from ui.navigation.lane_guidance_ui_if import LaneGuidance, LaneGuidanceUiIf


class LaneGuidanceUiStub(LaneGuidanceUiIf):
    """Ignore lane-guidance updates."""

    def set_lane_guidance(self, guidance: LaneGuidance | None) -> None:
        pass
