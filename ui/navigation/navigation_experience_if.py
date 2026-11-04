"""Shared navigation experience and places presentation contracts."""
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from ui.navigation.poi_models import PoiCategory, PointOfInterest, TransitMode


class NavigationExperience(str, Enum):
    ROAD = 'road'
    WAZE = 'waze'
    TERRAIN = 'terrain'


@dataclass(frozen=True, slots=True)
class NavigationExperienceState:
    selected: NavigationExperience = NavigationExperience.ROAD
    terrain_available: bool = False
    waze_available: bool = False
    waze_running: bool = False
    busy: bool = False
    waze_loading: bool = False


@dataclass(frozen=True, slots=True)
class NavigationPlacesDrawerState:
    places: tuple[PointOfInterest, ...] = ()
    status: str = 'Find places near the current map view.'


class NavigationExperienceRequestHandlerIf(Protocol):
    @property
    def state(self) -> NavigationExperienceState: ...

    def request_experience(self, experience: NavigationExperience) -> None: ...

    def request_saved_destination(self, key: str) -> None: ...

    def request_places(self) -> None:
        """Show the ORC places drawer, preserving any running Waze route."""
        ...

    def request_search_places(self, category: PoiCategory, transit: TransitMode = TransitMode.ALL) -> None: ...

    def request_select_place(self, place: PointOfInterest) -> None: ...

    def request_clear_places(self) -> None: ...

    def request_close_waze(self) -> None: ...
