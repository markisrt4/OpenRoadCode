# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op ground-track UI implementation."""

from ui.navigation.ground_track_ui_if import GroundTrackUiIf


class GroundTrackUiStub(GroundTrackUiIf):
    """Ignore speed-over-ground and course-over-ground updates."""

    def set_ground_speed(self, speed_mps: float | None) -> None:
        pass

    def set_course_over_ground(self, course_rad: float | None) -> None:
        pass
