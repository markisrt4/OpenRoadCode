"""Present normalized navigation state through narrow UI contracts."""

import math

from controllers.navigation.navigation_state import NavigationState
from ui.navigation import (
    GroundTrackUiIf,
    HeadingReference,
    OrientationUiIf,
    PositionFix,
    PositionUiIf,
    TranslationUiIf,
)


class NavigationStatePresenter:
    """Convert controller navigation snapshots into SI UI contract updates."""

    def __init__(
        self,
        *,
        orientation_ui: OrientationUiIf,
        translation_ui: TranslationUiIf,
        position_ui: PositionUiIf,
        ground_track_ui: GroundTrackUiIf,
    ) -> None:
        self._orientation_ui = orientation_ui
        self._translation_ui = translation_ui
        self._position_ui = position_ui
        self._ground_track_ui = ground_track_ui

    def present(self, state: NavigationState) -> None:
        """Publish one complete navigation snapshot.

        @param state Normalized controller snapshot to publish.
        """
        self._orientation_ui.set_heading(
            math.radians(state.heading_deg),
            HeadingReference.RELATIVE,
        )
        self._orientation_ui.set_pitch(math.radians(state.pitch_deg))
        self._orientation_ui.set_roll(math.radians(state.roll_deg))

        linear = state.linear_acceleration_mps2
        self._translation_ui.set_accel_x(linear.x)
        self._translation_ui.set_accel_y(linear.y)
        self._translation_ui.set_accel_z(linear.z)
        self._translation_ui.set_accel_total(
            math.sqrt(linear.x**2 + linear.y**2 + linear.z**2)
        )

        gps = state.gps
        if (
            gps is not None
            and gps.has_fix
            and gps.latitude_deg is not None
            and gps.longitude_deg is not None
        ):
            self._position_ui.set_position(
                PositionFix(
                    latitude_rad=math.radians(gps.latitude_deg),
                    longitude_rad=math.radians(gps.longitude_deg),
                    altitude_m=gps.altitude_m,
                    pfom_m=gps.accuracy_m,
                )
            )
            self._ground_track_ui.set_ground_speed(gps.speed_mps)
            self._ground_track_ui.set_course_over_ground(
                math.radians(gps.course_deg)
                if gps.course_deg is not None
                else None
            )
            return

        self._position_ui.set_position(None)
        self._ground_track_ui.set_ground_speed(None)
        self._ground_track_ui.set_course_over_ground(None)
