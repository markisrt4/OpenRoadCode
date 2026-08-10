"""Toolkit-neutral boundary for constructing Car UI destinations."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from apps.carUi.car_ui_dependencies import CarUiDependencies
from ui.screen_ui_if import ScreenUiIf


@dataclass(frozen=True, slots=True)
class CarUiScreens:
    """Contain every standard destination required by Car UI routes."""
    aircraft: ScreenUiIf
    weather: ScreenUiIf
    lighting: ScreenUiIf
    fm_radio: ScreenUiIf
    scanner: ScreenUiIf
    spotify: ScreenUiIf
    netflix: ScreenUiIf
    youtube: ScreenUiIf
    offroad_dashboard: ScreenUiIf
    vehicle_gauges: ScreenUiIf


class CarUiScreenFactoryIf(Protocol):
    """Construct standard Car UI destinations for one frontend toolkit."""

    def create_screens(
        self,
        dependencies: CarUiDependencies,
        on_frequency_changed: Callable[[int], None],
        dispatch: Callable[[Callable[[], None]], None],
    ) -> CarUiScreens:
        """Create, connect, and return all standard screen destinations.

        @param dependencies Runtime services and controllers used by screens.
        @param on_frequency_changed Callback for displayed frequency changes.
        @param dispatch Callback that schedules work on the frontend thread.
        @return Constructed set of standard Car UI destinations.
        """
        ...
