from abc import ABC, abstractmethod
from enum import Enum, auto

class HeadingReference(Enum):
    """Reference origin used by a supplied heading."""

    TRUE_NORTH = auto()
    MAGNETIC_NORTH = auto()
    RELATIVE = auto()


class OrientationUiIf(ABC):
    """Display vehicle attitude in a right-handed vehicle coordinate frame.

    The X axis points forward, Y points left, and Z points up. Roll is rotation
    about X and pitch is rotation about Y, following the right-hand rule.
    Heading is a bearing in ``[0, 2*pi)`` increasing clockwise from the
    selected true-north, magnetic-north, or user-defined relative reference.
    Heading is the navigation form of yaw, so a separate yaw setter is
    intentionally not exposed.

    ``None`` means the corresponding measurement is unavailable.
    """

    @abstractmethod
    def set_heading(
        self,
        heading_rad: float | None,
        reference: HeadingReference = HeadingReference.TRUE_NORTH,
    ) -> None:
        """Set heading in radians and identify its north reference.

        @param heading_rad Heading in radians, or None when unavailable.
        @param reference North reference used by the supplied heading.
        """
        ...

    @abstractmethod
    def set_pitch(self, pitch_rad: float | None) -> None:
        """Set pitch in radians, positive nose-up.

        @param pitch_rad Pitch in radians, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_roll(self, roll_rad: float | None) -> None:
        """Set roll using the vehicle-frame right-hand rule.

        @param roll_rad Roll in radians, or None when unavailable.
        """
        ...
