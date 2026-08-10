"""Lane-level route-guidance presentation contract."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto


class LaneDirection(Enum):
    """Describe a direction permitted by a travel lane."""

    STRAIGHT = auto()
    SLIGHT_LEFT = auto()
    LEFT = auto()
    SHARP_LEFT = auto()
    SLIGHT_RIGHT = auto()
    RIGHT = auto()
    SHARP_RIGHT = auto()
    U_TURN = auto()


@dataclass(frozen=True, slots=True)
class TravelLane:
    """Describe one lane and its route recommendation.

    @param directions Permitted travel directions for the lane.
    @param recommended Whether route guidance recommends this lane.
    @param active_direction Direction applicable to the current route.
    """

    directions: tuple[LaneDirection, ...]
    recommended: bool = False
    active_direction: LaneDirection | None = None


@dataclass(frozen=True, slots=True)
class LaneGuidance:
    """Contain the ordered lanes visible from left to right.

    @param lanes Ordered lane descriptions from left to right.
    """

    lanes: tuple[TravelLane, ...] = ()


class LaneGuidanceUiIf(ABC):
    """Display lane recommendations for the next route maneuver."""

    @abstractmethod
    def set_lane_guidance(self, guidance: LaneGuidance | None) -> None:
        """Replace lane guidance or clear unavailable guidance.

        @param guidance Current lane guidance, or None when unavailable.
        """
        ...
