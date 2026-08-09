"""UI contract for movement measured relative to the ground."""

from abc import ABC, abstractmethod


class GroundTrackUiIf(ABC):
    """Display speed and actual direction of travel over the ground.

    Ground track is distinct from vehicle heading: a vehicle can point in one
    direction while moving in another. ``None`` means a measurement is
    unavailable.
    """

    @abstractmethod
    def set_ground_speed(self, speed_mps: float | None) -> None:
        """Set speed over ground.

        @param speed_mps Speed in metres per second, or None.
        """
        ...

    @abstractmethod
    def set_course_over_ground(self, course_rad: float | None) -> None:
        """Set actual direction of travel over the ground.

        @param course_rad Clockwise radians from true north, or None.
        """
        ...
