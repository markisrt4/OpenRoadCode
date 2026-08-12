# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Provider-neutral turn-by-turn route presentation contract."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING

from ui.navigation.map_ui_if import GeoPoint

if TYPE_CHECKING:
    from ui.navigation.route_request_handler_if import RouteRequestHandlerIf


class TravelMode(Enum):
    """Identify the route costing mode requested by the user."""

    AUTO = auto()
    BICYCLE = auto()
    PEDESTRIAN = auto()
    TRANSIT = auto()


class NavigationStatus(Enum):
    """Describe the lifecycle of active route guidance."""

    IDLE = auto()
    CALCULATING = auto()
    ACTIVE = auto()
    RECALCULATING = auto()
    ARRIVED = auto()
    ERROR = auto()


class ManeuverType(Enum):
    """Classify a maneuver independently of routing-provider codes."""

    DEPART = auto()
    CONTINUE = auto()
    TURN_LEFT = auto()
    TURN_RIGHT = auto()
    KEEP_LEFT = auto()
    KEEP_RIGHT = auto()
    U_TURN = auto()
    MERGE = auto()
    ENTER_ROUNDABOUT = auto()
    EXIT_ROUNDABOUT = auto()
    EXIT = auto()
    ARRIVE = auto()


@dataclass(frozen=True, slots=True)
class RouteSummary:
    """Summarize the currently selected route.

    @param distance_m Remaining route distance in metres.
    @param duration_s Estimated remaining duration in seconds.
    @param estimated_arrival Estimated local or timezone-aware arrival time.
    """

    distance_m: float
    duration_s: float
    estimated_arrival: datetime | None = None


@dataclass(frozen=True, slots=True)
class RouteManeuver:
    """Describe the next turn-by-turn instruction.

    @param maneuver_type Provider-neutral maneuver category.
    @param instruction User-visible narrative instruction.
    @param distance_m Distance to the maneuver in metres.
    @param street_name Optional road or path name after the maneuver.
    @param bearing_after_rad Optional travel bearing after the maneuver.
    @param exit_number Optional numbered exit identifier.
    @param sign_text Optional sign or destination text.
    """

    maneuver_type: ManeuverType
    instruction: str
    distance_m: float
    street_name: str | None = None
    bearing_after_rad: float | None = None
    exit_number: str | None = None
    sign_text: str | None = None


@dataclass(frozen=True, slots=True)
class RouteGuidanceState:
    """Contain one complete turn-by-turn guidance snapshot.

    @param status Current route-guidance lifecycle state.
    @param destination Current destination, if selected.
    @param travel_mode Active route costing mode.
    @param summary Remaining route summary, if available.
    @param current_road Current road or path name.
    @param next_maneuver Next maneuver, if available.
    @param off_route Whether the current position is outside the route.
    @param voice_guidance_muted Whether spoken guidance is muted.
    @param status_message Optional user-visible status.
    @param error_message Optional user-visible routing error.
    """

    status: NavigationStatus
    destination: GeoPoint | None = None
    travel_mode: TravelMode = TravelMode.AUTO
    summary: RouteSummary | None = None
    current_road: str | None = None
    next_maneuver: RouteManeuver | None = None
    off_route: bool = False
    voice_guidance_muted: bool = False
    status_message: str | None = None
    error_message: str | None = None


class RouteGuidanceUiIf(ABC):
    """Display route guidance and emit semantic route requests."""

    @abstractmethod
    def set_route_guidance(self, state: RouteGuidanceState | None) -> None:
        """Replace route guidance or clear unavailable state.

        @param state Complete guidance snapshot, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_route_request_handler(
        self,
        handler: "RouteRequestHandlerIf | None",
    ) -> None:
        """Connect or clear the handler for semantic route requests.

        @param handler Request consumer, or None to disconnect it.
        """
        ...
