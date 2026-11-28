"""Shared navigation experience and places presentation contracts."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from ui.navigation.poi_models import PoiCategory, PointOfInterest, TransitMode
from ui.navigation.waze_gesture_if import WazeGesture


class NavigationExperience(str, Enum):
    ROAD = "road"
    WAZE = "waze"
    TERRAIN = "terrain"


@dataclass(frozen=True, slots=True)
class NavigationExperienceState:
    selected: NavigationExperience = NavigationExperience.ROAD
    terrain_available: bool = False
    waze_available: bool = False
    waze_running: bool = False
    busy: bool = False
    waze_loading: bool = False
    waze_gestures_available: bool = False
    waze_gestures_supported: bool = False
    waze_gesture_busy: bool = False
    waze_gesture_status: str = ""


@dataclass(frozen=True, slots=True)
class NavigationPlacesDrawerState:
    places: tuple[PointOfInterest, ...] = ()
    status: str = "Find places near the current map view."


class NavigationExperienceRequestHandlerIf(Protocol):
    @property
    def state(self) -> NavigationExperienceState:
        """Read the current immutable presentation state.

        @return Current immutable state.
        """
        ...

    def request_experience(self, experience: NavigationExperience) -> None:
        """Select the requested navigation experience.

        @param experience Navigation experience to display.
        """
        ...

    def request_saved_destination(self, key: str) -> None:
        """Navigate to a saved Home or Work location.

        @param key Saved destination key, home or work.
        """
        ...

    def request_places(self) -> None:
        """Show the ORC places drawer, preserving any running Waze route."""
        ...

    def request_search_places(
        self, category: PoiCategory, transit: TransitMode = TransitMode.ALL
    ) -> None:
        """Search for places in the requested category.

        @param category POI category to search.
        @param transit Transit mode filter for the search.
        """
        ...

    def request_select_place(self, place: PointOfInterest) -> None:
        """Select a discovered place for presentation.

        @param place Selected point of interest.
        """
        ...

    def request_clear_places(self) -> None:
        """Clear the current place search results."""
        ...

    def request_close_waze(self) -> None:
        """Close the retained Waze session."""
        ...

    def request_waze_gesture(self, gesture: WazeGesture) -> None:
        """Apply a gesture to the embedded Waze map.

        @param gesture Pan or zoom action to perform.
        """
        ...
