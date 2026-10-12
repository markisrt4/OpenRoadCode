# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""SI presentation values and semantic requests for navigation over video.

Sample timestamps use the local monotonic clock, matching VisionImage.
Navigation receipt times provide approximate alignment, not calibrated fusion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from ui.navigation.route_types import RouteTurn


class OverlayGpsStatus(str, Enum):
    NO_FIX = "no_fix"
    LIVE = "live"
    WEAK = "weak"
    CACHED = "cached"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class OverlayPosition:
    """One GPS observation, with local receipt time and SI accuracy."""
    timestamp_s: float
    has_fix: bool
    is_cached: bool = False
    accuracy_m: float | None = None


@dataclass(frozen=True, slots=True)
class OverlayMotion:
    """One ground-speed observation in metres per second."""
    timestamp_s: float
    speed_m_s: float | None
    is_cached: bool = False


@dataclass(frozen=True, slots=True)
class OverlayGuidance:
    """A route maneuver observed at a local monotonic receipt time."""
    timestamp_s: float
    instruction: str | None = None
    turn: RouteTurn = RouteTurn.UNKNOWN
    road_name: str | None = None
    distance_m: float | None = None
    off_route: bool = False
    complete: bool = False


@dataclass(frozen=True, slots=True)
class NavigationOverlayState:
    """Immutable navigation context for the currently displayed video frame."""
    enabled: bool = True
    instruction: str | None = None
    turn: RouteTurn = RouteTurn.UNKNOWN
    road_name: str | None = None
    distance_m: float | None = None
    speed_m_s: float | None = None
    gps_status: OverlayGpsStatus = OverlayGpsStatus.NO_FIX
    accuracy_m: float | None = None
    off_route: bool = False
    complete: bool = False
    guidance_stale: bool = False
    video_stale: bool = False
    frame_timestamp_s: float | None = None
    guidance_timestamp_s: float | None = None


class NavigationOverlayRequestHandlerIf(ABC):
    """Handle overlay visibility and screen lifecycle requests."""

    @abstractmethod
    def request_activate(self) -> None:
        """Activate presentation while Vision is visible."""

    @abstractmethod
    def request_deactivate(self) -> None:
        """Stop presentation and invalidate pending callbacks when hidden."""

    @abstractmethod
    def request_enabled(self, enabled: bool) -> None:
        """Show or hide guidance without affecting camera or route ownership.

        @param enabled Whether navigation guidance should be visible.
        """


class NavigationOverlayUiIf(ABC):
    """Receive navigation presentation without accessing navigation services."""
    @abstractmethod
    def set_navigation_overlay(self, state: NavigationOverlayState) -> None:
        """Present a complete immutable overlay snapshot.

        @param state SI navigation state selected for the displayed video frame.
        """

    @abstractmethod
    def set_navigation_overlay_handler(
        self, handler: NavigationOverlayRequestHandlerIf | None,
    ) -> None:
        """Bind or disconnect semantic overlay requests.

        @param handler Semantic request receiver, or None to disconnect it.
        """
